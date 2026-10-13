from glob import glob

from setuptools import find_packages, setup

package_name = 'rosorin_navigation'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/rviz', glob('rviz/*.rviz')),
        ('share/' + package_name + '/worlds', glob('worlds/*.sdf')),
        ('share/' + package_name + '/urdf', glob('urdf/*.xacro')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        # maps saved at the repository root (maps/house.yaml is the default map of navigation)
        ('share/' + package_name + '/maps', glob('../../maps/*.yaml') + glob('../../maps/*.pgm')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='minh',
    maintainer_email='minhsctn1608@gmail.com',
    description='Launch, config and navigation scripts for the ROSOrin Pro simulation',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'waypoint_follower = rosorin_navigation.waypoint_follower:main',
            'scan_noise = rosorin_navigation.scan_noise:main',
            'wheel_odometry = rosorin_navigation.wheel_odometry:main',
        ],
    },
)
