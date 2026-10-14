"""Cut the raw demo recording into the final video with burned-in subtitles.

Inputs (in the demo directory): raw.mkv, events.txt (seconds from the recording start), runs/*.csv,
maps/demo_house.pgm. Output: rosorin_demo_en.mp4 and its .ass subtitle file.
"""
import csv
import glob
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

D = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DEMO_DIR', '/tmp/rosorin_demo')
W, H = 1920, 1080
VW, VH = 1728, 958            # recorded 1834x1016 scaled, placed at the top; subtitle band below
VX = (W - VW) // 2
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FPS = 30

ev = {}
for fname, take in (('events.txt', 1), ('events2.txt', 2)):
    for line in open(os.path.join(D, fname)):
        t, name = line.split()
        ev[(take, name)] = float(t)

explore = list(csv.DictReader(open(sorted(glob.glob(os.path.join(D, 'runs', '*.csv')))[0])))
mission = list(csv.DictReader(open(sorted(glob.glob(os.path.join(D, 'runs2', '*.csv')))[-1])))
with open(os.path.join(D, 'maps', 'demo_house.pgm'), 'rb') as f:
    f.readline()
    map_w, map_h = (int(v) for v in f.readline().split())


def ok(rows):
    return sum(r['status'] == 'SUCCEEDED' for r in rows)


def mean(rows, key):
    return sum(float(r[key]) for r in rows) / max(len(rows), 1)


T = {
    'en': {
        's1': 'Step 1: start the simulation (Gazebo + ROS 2)',
        's1b': 'The ROSOrin Pro robot in the house',
        's2': 'Step 2: drive the robot: forward, sideways, turn',
        's3': 'Step 3: the LiDAR scan in RViz',
        's4': 'Step 4: SLAM: the robot explores the house and builds the map',
        's4b': 'The map grows room by room',
        's5': 'Step 5: save the map',
        's6': 'Step 6: navigation on the saved map',
        's6b': 'The robot drives to a goal in the bedroom',
        's7': 'Step 7: a mission through 7 waypoints',
        's7b': f'{ok(mission)}/{len(mission)} waypoints reached',
        'title': 'ROSOrin Pro: simulation, SLAM and navigation',
        'sub': 'ROS 2 Humble · Ignition Gazebo · slam_toolbox · Nav2',
        'end': 'Summary',
        'lines': [
            'The ROSOrin Pro simulated in Gazebo',
            'Driving and LiDAR',
            'Map built with SLAM and saved',
            'Navigation to a goal and through 7 waypoints',
        ],
    },
}

# (start event, end event, speed, [(subtitle key, fraction of the segment where it starts)], overlay)
SEGMENTS = [
    (1, 'rec_start', 's1_robot', 2.0, [('s1', 0.0)], None),
    (1, 's1_robot', 's2_drive', 1.0, [('s1b', 0.0)], None),
    (1, 's2_drive', 's2_end', 1.0, [('s2', 0.0)], None),
    (1, 's3_lidar', 's3_end', 1.0, [('s3', 0.0)], None),
    (1, 's4_slam', 's4_explore', 3.0, [('s4', 0.0)], None),
    (1, 's4_explore', 's4_end', 2.0, [('s4', 0.0), ('s4b', 0.45)], None),
    (1, 's5_save', 's5_end', 1.0, [('s5', 0.0)], 'map'),
    (2, 's6_nav', 's6_goal', 3.0, [('s6', 0.0)], None),
    (2, 's6_goal', 's6_end', 1.0, [('s6b', 0.0)], None),
    (2, 's7_wp', 's7_end', 2.0, [('s7', 0.0), ('s7b', 0.8)], None),
]


def card(path, lang, kind):
    img = Image.new('RGB', (W, H), (21, 24, 29))
    d = ImageDraw.Draw(img)
    t = T[lang]
    if kind == 'title':
        d.text((W // 2, 430), t['title'], font=ImageFont.truetype(FONT_B, 64), fill='white',
               anchor='mm')
        d.text((W // 2, 530), t['sub'], font=ImageFont.truetype(FONT, 34), fill=(160, 170, 185),
               anchor='mm')
        d.text((W // 2, 640), 'Nguyen Van Minh  ·  github.com/vminh16/rosorin-autonomy-sim',
               font=ImageFont.truetype(FONT, 28), fill=(120, 128, 140), anchor='mm')
    else:
        d.text((160, 220), t['end'], font=ImageFont.truetype(FONT_B, 60), fill='white')
        for i, line in enumerate(t['lines']):
            d.text((160, 340 + i * 90), '•  ' + line, font=ImageFont.truetype(FONT, 34),
                   fill=(215, 220, 228))
    img.save(path)


def ts(sec):
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f'{int(h)}:{int(m):02d}:{s:05.2f}'


def ass(lang, events):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,DejaVu Sans,34,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1.5,0,2,90,90,22,1
Style: Badge,DejaVu Sans,30,&H0000D7FF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,3,6,0,9,0,{W - VX - VW + 20},20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for start, end, style, text in events:
        if style == 'Sub':
            text = T[lang][text]
        lines.append(f'Dialogue: 0,{ts(start)},{ts(end)},{style},,0,0,0,,{text}')
    return head + '\n'.join(lines) + '\n'


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def main():
    work = os.path.join(D, 'post')
    os.makedirs(work, exist_ok=True)
    mp = os.path.join(work, 'map.png')
    m = Image.open(os.path.join(D, 'maps', 'demo_house.pgm')).convert('RGB')
    m = m.resize((m.width * 3, m.height * 3), Image.NEAREST)
    framed = Image.new('RGB', (m.width + 12, m.height + 12), (255, 200, 0))
    framed.paste(m, (6, 6))
    framed.save(mp)

    parts, timeline, t = [], [], 0.0
    # title card
    for kind, dur in (('title', 5.0),):
        p = os.path.join(work, 'title.mp4')
        card(os.path.join(work, 'title_en.png'), 'en', 'title')
        parts.append(('card', 'title', dur))
        t += dur
    for i, (take, a, b, speed, subs, overlay) in enumerate(SEGMENTS):
        raw = os.path.join(D, 'raw.mkv' if take == 1 else 'raw2.mkv')
        start, end = ev[(take, a)], ev[(take, b)]
        out_len = (end - start) / speed
        seg = os.path.join(work, f'seg{i:02d}.mp4')
        vf = (f'trim=start={start:.2f}:end={end:.2f},setpts=(PTS-STARTPTS)/{speed},'
              f'scale={VW}:{VH},pad={W}:{H}:{VX}:0:color=0x15181d,fps={FPS}')
        inputs = ['-i', raw]
        if overlay == 'map':
            inputs += ['-i', mp]
            vf = f'[0:v]{vf}[v];[v][1:v]overlay=x={VX + VW - framed.width - 30}:y=60[out]'
            run(['ffmpeg', '-y', *inputs, '-filter_complex', vf, '-map', '[out]', '-an',
                 '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', seg])
        else:
            run(['ffmpeg', '-y', *inputs, '-vf', vf, '-an', '-c:v', 'libx264', '-preset', 'medium',
                 '-crf', '18', '-pix_fmt', 'yuv420p', seg])
        for k, (key, frac) in enumerate(subs):
            s0 = t + frac * out_len
            s1 = t + (subs[k + 1][1] * out_len if k + 1 < len(subs) else out_len)
            timeline.append((s0, s1, 'Sub', key))
        if speed > 1:
            timeline.append((t, t + out_len, 'Badge', f'×{speed:g}'))
        parts.append(('seg', seg, out_len))
        t += out_len
    parts.append(('card', 'end', 8.0))
    total = t + 8.0

    for lang in ('en',):
        files = []
        for kind, what, dur in parts:
            if kind == 'card':
                png = os.path.join(work, f'{what}_{lang}.png')
                card(png, lang, what)
                mp4 = os.path.join(work, f'{what}_{lang}.mp4')
                run(['ffmpeg', '-y', '-loop', '1', '-t', f'{dur}', '-i', png, '-vf', f'fps={FPS}',
                     '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                     mp4])
                files.append(mp4)
            else:
                files.append(what)
        lst = os.path.join(work, f'list_{lang}.txt')
        with open(lst, 'w') as f:
            f.writelines(f"file '{p}'\n" for p in files)
        joined = os.path.join(work, f'joined_{lang}.mp4')
        run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', joined])
        sub = os.path.join(D, f'rosorin_demo_{lang}.ass')
        with open(sub, 'w') as f:
            f.write(ass(lang, timeline))
        out = os.path.join(D, f'rosorin_demo_{lang}.mp4')
        run(['ffmpeg', '-y', '-i', joined, '-vf', f'ass={sub}', '-c:v', 'libx264', '-preset',
             'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out])
        print(out, f'{total:.1f} s')


if __name__ == '__main__':
    main()
