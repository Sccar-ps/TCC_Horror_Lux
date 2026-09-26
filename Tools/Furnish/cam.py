# Posiciona a camera do viewport do editor:  py ".../Tools/Furnish/cam.py" x y z pitch yaw
import sys, unreal
a = [float(v) for v in sys.argv[1:6]]
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
ues.set_level_viewport_camera_info(unreal.Vector(a[0], a[1], a[2]), unreal.Rotator(roll=0.0, pitch=a[3], yaw=a[4]))
