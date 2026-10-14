// Copyright 2026 Nguyen Van Minh. Licensed under the Apache License, Version 2.0 (see LICENSE).
//
// Traction-limited planar drive for the ROSOrin Pro simulation (Ignition Gazebo Fortress).
//
// Replaces ignition::gazebo::systems::VelocityControl, which overwrites the full body velocity
// every step: the robot then pushes with unlimited force, climbs obstacles, keeps any tilt
// (angular velocity is overwritten too) and flies off once tilted, because gravity can no longer
// act (ISSUE-016). This system instead applies a horizontal force and a yaw torque to the
// canonical link, as the wheels would:
//   F   = m (v_cmd - v) / tau,        |F|   <= mu m g          (traction limit)
//   T_z = I_zz (w_cmd - w_z) / tau,   |T_z| <= mu m g * lever  (same limit at the wheels)
// v_cmd is the commanded body twist rotated by the yaw only. z, roll and pitch are left to the
// physics engine, so gravity, contacts and settling work as usual. The wheels are frictionless
// (see rosorin_navigation/urdf/wheel.xacro), so this force is the only drive.
//
// Parameters (all optional):
//   <topic>               Twist topic                         default /cmd_vel
//   <traction_coefficient> mu, ground-wheel friction          default 0.6
//   <lever_arm>           (wheelbase + track) / 2, m          default 0.174355 (Hiwonder wiki)
//   <time_constant>       tau, velocity response time, s      default 0.1
//   <max_tilt>            no drive above this roll/pitch, rad default 0.5 (wheels off the ground)
//   <wheel_radius>        m                                   default 0.04 (wiki: diameter 0.08)
//   <max_wheel_speed>     motor limit, rad/s                  default 11.519 (110 rpm no-load, wiki
//                         1.10.2.3): 0.461 m/s straight, 2.64 rad/s turning

#include <ignition/msgs/twist.pb.h>

#include <algorithm>
#include <cmath>
#include <mutex>
#include <string>

#include <ignition/gazebo/components/Gravity.hh>
#include <ignition/gazebo/components/Inertial.hh>
#include <ignition/gazebo/components/Pose.hh>
#include <ignition/gazebo/Link.hh>
#include <ignition/gazebo/Model.hh>
#include <ignition/gazebo/System.hh>
#include <ignition/gazebo/Util.hh>
#include <ignition/math/Vector3.hh>
#include <ignition/plugin/Register.hh>
#include <ignition/transport/Node.hh>

namespace rosorin
{
namespace gz = ignition::gazebo;
namespace math = ignition::math;

class PlanarDrive
  : public gz::System,
  public gz::ISystemConfigure,
  public gz::ISystemPreUpdate
{
public:
  void Configure(
    const gz::Entity & _entity, const std::shared_ptr<const sdf::Element> & _sdf,
    gz::EntityComponentManager & _ecm, gz::EventManager &) override
  {
    model_ = gz::Model(_entity);
    if (!model_.Valid(_ecm)) {
      ignerr << "PlanarDrive must be attached to a model.\n";
      return;
    }
    link_ = gz::Link(model_.CanonicalLink(_ecm));
    link_.EnableVelocityChecks(_ecm, true);
    // WorldInertialPose / WorldInertiaMatrix read the WorldPose component, off by default
    for (const auto & entity : model_.Links(_ecm)) {
      gz::enableComponent<gz::components::WorldPose>(_ecm, entity);
    }

    const std::string topic = _sdf->Get<std::string>("topic", "/cmd_vel").first;
    mu_ = _sdf->Get<double>("traction_coefficient", 0.6).first;
    lever_ = _sdf->Get<double>("lever_arm", 0.174355).first;
    tau_ = _sdf->Get<double>("time_constant", 0.1).first;
    max_tilt_ = _sdf->Get<double>("max_tilt", 0.5).first;
    wheel_radius_ = _sdf->Get<double>("wheel_radius", 0.04).first;
    max_wheel_speed_ = _sdf->Get<double>("max_wheel_speed", 11.519).first;
    node_.Subscribe(topic, &PlanarDrive::OnCmd, this);
    ignmsg << "PlanarDrive listening on [" << topic << "], mu " << mu_ << ", tau " << tau_ <<
      " s\n";
  }

  void PreUpdate(const gz::UpdateInfo & _info, gz::EntityComponentManager & _ecm) override
  {
    if (_info.paused || !link_.Valid(_ecm)) {
      return;
    }
    if (mass_ <= 0.0 && !ComputeMass(_ecm)) {
      if (++mass_attempts_ == 100) {
        ignwarn << "PlanarDrive: could not read the model mass, the robot will not move.\n";
      }
      return;
    }
    const auto pose = link_.WorldInertialPose(_ecm);
    const auto w = link_.WorldAngularVelocity(_ecm);
    if (!pose || !w) {
      return;
    }
    const auto v = link_.WorldLinearVelocity(_ecm, com_offset_);
    if (!v) {
      return;
    }
    const math::Quaterniond rot = link_.WorldPose(_ecm)->Rot();
    if (std::abs(rot.Roll()) > max_tilt_ || std::abs(rot.Pitch()) > max_tilt_) {
      return;  // the wheels have lost the ground: no traction
    }

    double vx, vy, wz;
    {
      std::lock_guard<std::mutex> lock(mutex_);
      vx = cmd_vx_;
      vy = cmd_vy_;
      wz = cmd_wz_;
    }
    // the fastest mecanum wheel turns at (|vx| + |vy| + lever |wz|) / r; above the motor limit the
    // whole command is scaled down, keeping its direction
    const double wheel_max = (std::abs(vx) + std::abs(vy) + lever_ * std::abs(wz)) / wheel_radius_;
    if (wheel_max > max_wheel_speed_) {
      const double k = max_wheel_speed_ / wheel_max;
      vx *= k;
      vy *= k;
      wz *= k;
    }
    const double c = std::cos(rot.Yaw());
    const double s = std::sin(rot.Yaw());
    const math::Vector3d v_cmd(c * vx - s * vy, s * vx + c * vy, 0.0);
    math::Vector3d force = mass_ * (v_cmd - math::Vector3d(v->X(), v->Y(), 0.0)) / tau_;
    if (force.Length() > max_force_) {
      force = force.Normalized() * max_force_;
    }
    const double torque = std::clamp(
      izz_ * (wz - w->Z()) / tau_, -max_force_ * lever_, max_force_ * lever_);
    // AddWorldWrench applies at the link origin (base_footprint, on the floor): move the force
    // to the centre of mass so that driving does not pitch the body
    const math::Vector3d arm = pose->Pos() - link_.WorldPose(_ecm)->Pos();
    link_.AddWorldWrench(_ecm, force, math::Vector3d(0.0, 0.0, torque) + arm.Cross(force));
  }

private:
  void OnCmd(const ignition::msgs::Twist & _msg)
  {
    std::lock_guard<std::mutex> lock(mutex_);
    cmd_vx_ = _msg.linear().x();
    cmd_vy_ = _msg.linear().y();
    cmd_wz_ = _msg.angular().z();
  }

  // Total mass of the model and its yaw inertia about the canonical link's centre of mass.
  bool ComputeMass(gz::EntityComponentManager & _ecm)
  {
    const auto base = link_.WorldInertialPose(_ecm);
    const auto * base_inertial = _ecm.Component<gz::components::Inertial>(link_.Entity());
    if (!base || !base_inertial) {
      return false;
    }
    com_offset_ = base_inertial->Data().Pose().Pos();
    double mass = 0.0;
    double izz = 0.0;
    for (const auto & entity : model_.Links(_ecm)) {
      gz::Link link(entity);
      const auto * inertial = _ecm.Component<gz::components::Inertial>(entity);
      const auto pose = link.WorldInertialPose(_ecm);
      const auto inertia = link.WorldInertiaMatrix(_ecm);
      if (!inertial || !pose || !inertia) {
        return false;
      }
      const double m = inertial->Data().MassMatrix().Mass();
      const math::Vector3d d = pose->Pos() - base->Pos();
      mass += m;
      izz += (*inertia)(2, 2) + m * (d.X() * d.X() + d.Y() * d.Y());
    }
    double g = 9.8;
    const auto world = gz::worldEntity(_ecm);
    if (const auto * gravity = _ecm.Component<gz::components::Gravity>(world)) {
      g = gravity->Data().Length();
    }
    mass_ = mass;
    izz_ = izz;
    max_force_ = mu_ * mass_ * g;
    ignmsg << "PlanarDrive: mass " << mass_ << " kg, Izz " << izz_ << " kg m2, max force " <<
      max_force_ << " N\n";
    return mass_ > 0.0;
  }

  gz::Model model_{gz::kNullEntity};
  gz::Link link_{gz::kNullEntity};
  ignition::transport::Node node_;
  std::mutex mutex_;
  double cmd_vx_{0.0}, cmd_vy_{0.0}, cmd_wz_{0.0};
  double mu_{0.6}, lever_{0.174355}, tau_{0.1}, max_tilt_{0.5};
  double wheel_radius_{0.04}, max_wheel_speed_{11.519};
  double mass_{0.0}, izz_{0.0}, max_force_{0.0};
  int mass_attempts_{0};
  math::Vector3d com_offset_;
};
}  // namespace rosorin

IGNITION_ADD_PLUGIN(
  rosorin::PlanarDrive, ignition::gazebo::System,
  rosorin::PlanarDrive::ISystemConfigure, rosorin::PlanarDrive::ISystemPreUpdate)
IGNITION_ADD_PLUGIN_ALIAS(rosorin::PlanarDrive, "rosorin::PlanarDrive")
