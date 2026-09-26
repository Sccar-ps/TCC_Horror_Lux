# Referencia de escala temporaria: coloca o Cowboy (malha do jogador) em pe em pontos da casa.
#   py ".../Tools/Furnish/ref_person.py"         -> cria (tag LUX_REF, pasta LUX/Referencia)
#   py ".../Tools/Furnish/ref_person.py" clear   -> remove
# Nao tem colisao e nao aparece no jogo (hidden in game). Remova antes de salvar o mapa.
import sys, unreal

TAG = "LUX_REF"
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for a in unreal.GameplayStatics.get_all_actors_with_tag(w, TAG):
    eas.destroy_actor(a)
if len(sys.argv) > 1 and sys.argv[1] == "clear":
    raise SystemExit
skm = unreal.load_asset("/Game/Characters/MixamoFP/Mesh/SKM_Cowboy_NoGun")
SPOTS = [("Ref_Sala_TV", -2180, -560, 180), ("Ref_Sala_Jantar", -2470, -1250, 0), ("Ref_Sala_Porta", -2300, -1830, 90),
         ("Ref_Corredor", -3275, 150, 0), ("Ref_Quarto", -2760, 1440, 90), ("Ref_Escritorio", -3690, -1000, 180)]
with unreal.ScopedEditorTransaction("LUX: referencia de escala"):
    for lab, x, y, yaw in SPOTS:
        a = eas.spawn_actor_from_object(skm, unreal.Vector(x, y, 0), unreal.Rotator(roll=0, pitch=0, yaw=yaw - 90))
        a.set_actor_label(lab)
        a.tags = [unreal.Name(TAG)]
        a.set_folder_path("LUX/Referencia")
        a.set_actor_hidden_in_game(True)
        c = a.get_component_by_class(unreal.SkeletalMeshComponent)
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        org, ext = a.get_actor_bounds(False)
        unreal.log("LUXREF %s altura %.1f cm" % (lab, ext.z * 2))
