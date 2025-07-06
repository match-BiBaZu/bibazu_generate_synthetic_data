import bpy
import os
import math
import random
from mathutils import Vector
import csv
from mathutils import Quaternion
# ---------- CONFIG ---------------------------------------------------
OBJ_NAME      = "Df4a"
OUT_ROOT      = r"C:\Users\User\Desktop\MATCH\Ql"
RES           = 640
IMG_NAME      = "shot.jpg"
SCALE_FACTOR  = 0.5

PLANE_SIZE    = 500
GREY_RANGE    = (0.05, 0.15)

LIGHT_COUNT   = 6
LIGHT_PWR     = 1400
LIGHT_Z_OFF   = 7
MARGIN        = 10




def load_poses_from_csv(filepath):
    poses = {}
    with open(filepath, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            pose_id = row["PoseID"]
            x = float(row["QuatX"])
            y = float(row["QuatY"])
            z = float(row["QuatZ"])
            w = float(row["QuatW"])
            name = f"Pose_{pose_id}"
            poses[name] = Quaternion((w, x, y, z))
    return poses

CSV_PATH = r"C:\Users\User\Desktop\MATCH\CSV Posses\Df4a_candidate_rotations.csv"
POSES = load_poses_from_csv(CSV_PATH)


# ---------- UTILITIES ------------------------------------------------
def get_part():
    if OBJ_NAME not in bpy.data.objects:
        raise RuntimeError(f'Object "{OBJ_NAME}" not found.')
    return bpy.data.objects[OBJ_NAME]

def bb_min(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs, ys, zs = zip(*pts)
    return Vector((min(xs), min(ys), min(zs)))

def bb_minmax(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs, ys, zs = zip(*pts)
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))

def flip_x(vec):
    return Vector((-vec.x, vec.y, vec.z))

def clear_scene():
    for o in bpy.data.objects:
        if o.type == 'LIGHT' or o.name.startswith("Plane_"):
            bpy.data.objects.remove(o, do_unlink=True)

# ---------- PREPARE OBJECT -------------------------------------------
def prepare_part_fixed():
    o = get_part()
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bb_corner = bb_min(o)
    o.location -= bb_corner

    o.scale = (SCALE_FACTOR,) * 3
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bb_corner = bb_min(o)
    o.location -= bb_corner
    bpy.context.view_layer.update()

    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    o.rotation_mode = "QUATERNION"

# ---------- BACKDROP PLANES -----------------------------------------
def backdrop_planes():
    mat = bpy.data.materials.get("PTFE_White") or bpy.data.materials.new("PTFE_White")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
    bsdf.inputs["Roughness"].default_value = 0.85
    spec_input = bsdf.inputs.get("Specular") or bsdf.inputs.get("Specular IOR Level")
    if spec_input:
        spec_input.default_value = 0.02

    for rot, name in ((0, "Plane_XY"), (1.5708, "Plane_ZY")):
        bpy.ops.mesh.primitive_plane_add(size=PLANE_SIZE)
        p = bpy.context.active_object
        p.name = name
        p.rotation_euler[1] = rot
        p.location = flip_x(p.location)
        p.data.materials.append(mat)

# ---------- MATERIAL -------------------------------------------------
def apply_grey():
    v = random.uniform(*GREY_RANGE)
    mat = bpy.data.materials.new("GreyMat")
    mat.diffuse_color = (v, v, v, 1)
    o = get_part()
    o.data.materials.clear()
    o.data.materials.append(mat)

# ---------- LIGHTS (FLIPPED WITH OBJECT!) ------------------------------
def build_lights(obj):
    (xmin, xmax), (ymin, ymax), (_, zmax) = bb_minmax(obj)

    # فقط ناحیه منفی محور X
    if xmax > 0:
        xmax = 0  # اطمینان از اینکه x مثبت حذف می‌شه

    x_span = abs(xmin - xmax) + 2 * MARGIN
    y_span = ymax - ymin + 2 * MARGIN

    cols = math.ceil(math.sqrt(LIGHT_COUNT))
    rows = math.ceil(LIGHT_COUNT / cols)

    # پخش نور در ناحیه x منفی
    xs = [xmax - MARGIN - i * x_span / (cols - 1 if cols > 1 else 1) for i in range(cols)]
    ys = [ymin - MARGIN + j * y_span / (rows - 1 if rows > 1 else 1) for j in range(rows)]

    coords = [(x, y) for y in ys for x in xs][:LIGHT_COUNT]  # دقیقاً LIGHT_COUNT تا

    for i, (x, y) in enumerate(coords, 1):
        light = bpy.data.lights.new(f"Light_{i}", type='POINT')
        light.energy = LIGHT_PWR
        light_obj = bpy.data.objects.new(f"Light_{i}", light)
        light_obj.location = Vector((x, y, zmax + LIGHT_Z_OFF))
        bpy.context.collection.objects.link(light_obj)



# ---------- RENDER FUNCTION ------------------------------------------
def render_to(folder_path, name):
    scene = bpy.context.scene
    scene.render.resolution_x = scene.render.resolution_y = RES
    scene.render.resolution_percentage = 100
    os.makedirs(folder_path, exist_ok=True)
    scene.render.filepath = os.path.join(folder_path, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("✅ Rendered:", scene.render.filepath)

# ---------- MAIN ------------------------------------------------------
clear_scene()
prepare_part_fixed()
backdrop_planes()
apply_grey()

obj = get_part()
for pose_name, quat in POSES.items():
    print(f"🎯 Rendering {pose_name}")
    obj.rotation_quaternion = quat
    bpy.context.view_layer.update()

    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    min_corner = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    obj.location -= min_corner
    obj.location = flip_x(obj.location)
    bpy.context.view_layer.update()

    for l in [o for o in bpy.data.objects if o.type == 'LIGHT']:
        bpy.data.objects.remove(l, do_unlink=True)

    build_lights(obj)
    render_to(os.path.join(OUT_ROOT, pose_name), pose_name)
