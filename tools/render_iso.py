"""Furniture Kit 모델을 Kenney 'Isometric Miniature' 규격으로 다시 렌더한다.

왜 다시 렌더하나 — Furniture Kit 의 기성 Isometric PNG 는 오브젝트마다 다르게 크롭돼
있어 타일 격자에 맞출 기준점이 없다. Miniature 시리즈는 256x512 균일 캔버스에
2:1 격자(256x128)로 렌더돼 있어 그냥 얹으면 맞는다. 그 규격으로 통일한다.

    blender.exe -b -P render_iso.py -- <models_dir> <out_dir> [이름 ...]
"""
import math
import sys
from pathlib import Path

import bpy

# --- Miniature 규격 (실측) --------------------------------------------------
# 캔버스 — 타일 다이아몬드는 256×128 그대로 두고 옆·위로 여백을 준다.
# 256 폭으로 렌더하면 책장처럼 타일 밖으로 나가는 오브젝트가 잘린다 (실측: 왼쪽 여백 0).
W, H = 384, 768
TILE_W, TILE_H = 256, 128  # 1x1 타일이 만드는 다이아몬드 (2:1)
# 2:1 dimetric: 지면을 45도 돌리고 X 로 60도 기울이면 높이/폭 = cos60 = 0.5
CAM_TILT = math.radians(60.0)
# Blender 의 ortho_scale 은 해상도가 큰 쪽(여기선 세로 512)에 대응한다.
# 다이아몬드 폭 √2 유닛이 256px 이 되려면 512/ortho = 256/√2 → ortho = 2√2.
ORTHO = 2.0 * math.sqrt(2.0) * (H / 512)   # 세로 해상도에 비례. 타일 폭은 256 으로 유지된다

SHIFT_Y = 0.4267         # 실측: 허리를 y=704(=H-TILE_H/2)에 맞춘다
FACES = {"SE": 45.0, "SW": 135.0, "NW": 225.0, "NE": 315.0}


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"       # 플랫한 Kenney 룩에 가깝다
    sh = sc.display.shading
    sh.light = "STUDIO"          # 면별 음영을 남긴다. 어두워지는 것은 뒤에서 보정한다
    sh.color_type = "MATERIAL"   # glb 는 텍스처가 아니라 머티리얼 색을 쓴다
    sh.show_shadows = False
    sh.show_cavity = False
    sc.render.resolution_x = W
    sc.render.resolution_y = H
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"


def make_camera(z_deg):
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ORTHO
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    # Blender 안에서 실제로 찍어 보니 모델은 x[0,1] y[0,1] z[0,h] 에 놓인다
    # (OBJ 파일의 부호와 다르다). 타일 중심은 (0.5, 0.5, 0).
    target = (0.5, 0.5, 0.0)
    dist = 10.0
    z = math.radians(z_deg)
    cam.location = (
        target[0] + dist * math.sin(CAM_TILT) * math.sin(z),
        target[1] - dist * math.sin(CAM_TILT) * math.cos(z),
        target[2] + dist * math.cos(CAM_TILT),
    )
    cam.rotation_euler = (CAM_TILT, 0.0, z)

    # 캔버스는 세로로 2배다. 다이아몬드가 아래쪽에 오도록 카메라를 위로 민다.
    # 화면 세로 절반(= ORTHO 만큼)의 1/2 을 올리면 아래 절반에 타일이 놓인다.
    cam_data.shift_y = SHIFT_Y
    return cam


def load(path):
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def render_one(model: Path, out_dir: Path):
    for face, z_deg in FACES.items():
        clear()
        setup_scene()
        load(model)
        make_camera(z_deg)
        bpy.context.scene.render.filepath = str(out_dir / f"{model.stem}_{face}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    models_dir, out_dir = Path(argv[0]), Path(argv[1])
    names = argv[2:]
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = [models_dir / f"{n}.glb" for n in names] if names else sorted(models_dir.glob("*.glb"))
    for m in targets:
        if not m.exists():
            print(f"  없음: {m}")
            continue
        print(f"  렌더 {m.stem}")
        render_one(m, out_dir)


main()
