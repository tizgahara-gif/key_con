bl_info = {
    "name": "Blender 5 Key Press Display",
    "author": "Your Name",
    "version": (0, 2, 0),
    "blender": (5, 0, 0),
    "location": "View3D / Image Editor / Node Editor",
    "description": "Display pressed keys in real time with history and auto clear",
    "category": "Interface",
}

import time

import blf
import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty

STATE = {
    "running": False,
    "history": [],  # [{"text": str, "time": float, "area": str}]
    "draw_handlers": {},
    "timer": None,
}

ADDON_KEYMAPS = []
TARGET_SPACES = {
    "VIEW_3D": bpy.types.SpaceView3D,
    "IMAGE_EDITOR": bpy.types.SpaceImageEditor,
    "NODE_EDITOR": bpy.types.SpaceNodeEditor,
}
MODIFIER_LABELS = {
    "ctrl": "Ctrl",
    "shift": "Shift",
    "alt": "Alt",
    "oskey": "Cmd",
}
EVENT_TYPE_LABELS = {
    "LEFTMOUSE": "LMB",
    "MIDDLEMOUSE": "MMB",
    "RIGHTMOUSE": "RMB",
    "WHEELUPMOUSE": "WheelUp",
    "WHEELDOWNMOUSE": "WheelDown",
    "WHEELINMOUSE": "WheelIn",
    "WHEELOUTMOUSE": "WheelOut",
    "RET": "Enter",
    "ESC": "Esc",
    "SPACE": "Space",
    "DEL": "Delete",
    "BACK_SPACE": "Backspace",
    "LEFT_ARROW": "Left",
    "RIGHT_ARROW": "Right",
    "UP_ARROW": "Up",
    "DOWN_ARROW": "Down",
    "PAGE_UP": "PageUp",
    "PAGE_DOWN": "PageDown",
}
IGNORE_EVENT_TYPES = {
    "MOUSEMOVE",
    "INBETWEEN_MOUSEMOVE",
    "WINDOW_DEACTIVATE",
    "TIMER",
}


class KEYCON_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    pos_x: IntProperty(name="X", default=32, min=0)
    pos_y: IntProperty(name="Y", default=120, min=0)
    font_size: IntProperty(name="Font Size", default=20, min=10, max=96)
    max_history: IntProperty(name="Max History", default=6, min=1, max=30)
    ttl_seconds: FloatProperty(name="TTL (sec)", default=2.0, min=0.2, max=10.0)

    show_modifiers: BoolProperty(name="Show Modifiers", default=True)
    show_area: BoolProperty(name="Show Area", default=False)

    target_view_3d: BoolProperty(name="View3D", default=True)
    target_image_editor: BoolProperty(name="Image Editor", default=True)
    target_node_editor: BoolProperty(name="Node Editor", default=True)

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.label(text="Display")
        row = col.row(align=True)
        row.prop(self, "pos_x")
        row.prop(self, "pos_y")
        col.prop(self, "font_size")
        col.prop(self, "max_history")
        col.prop(self, "ttl_seconds")

        col = layout.column(align=True)
        col.label(text="Shown Items")
        col.prop(self, "show_modifiers")
        col.prop(self, "show_area")

        col = layout.column(align=True)
        col.label(text="Target Areas")
        row = col.row(align=True)
        row.prop(self, "target_view_3d")
        row.prop(self, "target_image_editor")
        row.prop(self, "target_node_editor")


def _prefs():
    addon = bpy.context.preferences.addons.get(__name__)
    return addon.preferences if addon else None


def _enabled_area_types(prefs):
    area_types = []
    if prefs.target_view_3d:
        area_types.append("VIEW_3D")
    if prefs.target_image_editor:
        area_types.append("IMAGE_EDITOR")
    if prefs.target_node_editor:
        area_types.append("NODE_EDITOR")
    return area_types


def _pretty_key_name(event_type):
    if event_type in EVENT_TYPE_LABELS:
        return EVENT_TYPE_LABELS[event_type]

    if len(event_type) == 1:
        return event_type.upper()

    return event_type.replace("_", " ").title()


def _format_event_text(event, prefs):
    parts = []

    if prefs.show_modifiers:
        for attr in ("ctrl", "shift", "alt", "oskey"):
            if getattr(event, attr, False):
                parts.append(MODIFIER_LABELS[attr])

    key_name = _pretty_key_name(event.type)
    if key_name not in parts:
        parts.append(key_name)

    return "+".join(parts)


def _append_history(text, area_type):
    prefs = _prefs()
    if not prefs:
        return

    STATE["history"].append({"text": text, "time": time.monotonic(), "area": area_type})
    STATE["history"] = STATE["history"][-prefs.max_history :]


def _prune_history():
    prefs = _prefs()
    if not prefs:
        return

    now = time.monotonic()
    ttl = prefs.ttl_seconds
    STATE["history"] = [item for item in STATE["history"] if now - item["time"] <= ttl]


def _tag_redraw_targets():
    wm = bpy.context.window_manager
    if not wm:
        return

    for window in wm.windows:
        screen = window.screen
        if not screen:
            continue
        for area in screen.areas:
            if area.type in TARGET_SPACES:
                area.tag_redraw()


def _draw_history(area_type):
    prefs = _prefs()
    if not prefs or not STATE["running"]:
        return

    if area_type not in _enabled_area_types(prefs):
        return

    now = time.monotonic()
    items = [
        item
        for item in STATE["history"]
        if now - item["time"] <= prefs.ttl_seconds
    ]

    if not items:
        return

    blf.size(0, prefs.font_size)
    line_height = int(prefs.font_size * 1.35)

    x = prefs.pos_x
    y = prefs.pos_y

    for i, item in enumerate(reversed(items[-prefs.max_history:])):
        age = now - item["time"]
        alpha = max(0.0, min(1.0, 1.0 - (age / max(0.001, prefs.ttl_seconds))))

        text = item["text"]
        if prefs.show_area:
            text = f"[{item['area']}] {text}"

        blf.position(0, x, y + (i * line_height), 0)
        blf.color(0, 1.0, 1.0, 1.0, alpha)
        blf.draw(0, text)


def _rebuild_draw_handlers():
    _remove_draw_handlers()

    prefs = _prefs()
    if not prefs:
        return

    for area_type in _enabled_area_types(prefs):
        space_cls = TARGET_SPACES[area_type]
        handler = space_cls.draw_handler_add(_draw_history, (area_type,), "WINDOW", "POST_PIXEL")
        STATE["draw_handlers"][area_type] = (space_cls, handler)


def _remove_draw_handlers():
    for _, (space_cls, handler) in list(STATE["draw_handlers"].items()):
        space_cls.draw_handler_remove(handler, "WINDOW")
    STATE["draw_handlers"].clear()


class KEYCON_OT_toggle_display(bpy.types.Operator):
    """Start/Stop key press overlay"""

    bl_idname = "keycon.toggle_display"
    bl_label = "Toggle Key Display"

    def invoke(self, context, event):
        if STATE["running"]:
            STATE["running"] = False
            self.report({"INFO"}, "Key display: OFF")
            _tag_redraw_targets()
            return {"FINISHED"}

        prefs = _prefs()
        if not prefs:
            self.report({"ERROR"}, "Addon preferences are unavailable")
            return {"CANCELLED"}

        if not _enabled_area_types(prefs):
            self.report({"WARNING"}, "Enable at least one target area in preferences")
            return {"CANCELLED"}

        STATE["running"] = True
        STATE["history"].clear()
        _rebuild_draw_handlers()

        wm = context.window_manager
        STATE["timer"] = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        self.report({"INFO"}, "Key display: ON")
        _tag_redraw_targets()
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if not STATE["running"]:
            if STATE["timer"]:
                context.window_manager.event_timer_remove(STATE["timer"])
                STATE["timer"] = None
            _remove_draw_handlers()
            _tag_redraw_targets()
            return {"CANCELLED"}

        if event.type == "TIMER":
            _prune_history()
            _tag_redraw_targets()
            return {"PASS_THROUGH"}

        if event.value == "PRESS" and event.type not in IGNORE_EVENT_TYPES:
            prefs = _prefs()
            if prefs:
                area_type = context.area.type if context.area else "UNKNOWN"
                event_text = _format_event_text(event, prefs)
                _append_history(event_text, area_type)
                _tag_redraw_targets()

        return {"PASS_THROUGH"}


class KEYCON_PT_panel(bpy.types.Panel):
    bl_label = "KeyCon Display"
    bl_idname = "KEYCON_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"

    def draw(self, context):
        layout = self.layout
        label = "Stop" if STATE["running"] else "Start"
        layout.operator(KEYCON_OT_toggle_display.bl_idname, text=f"{label} Key Display")

        prefs = _prefs()
        if prefs:
            layout.label(text=f"History: {len(STATE['history'])}/{prefs.max_history}")


classes = (
    KEYCON_Preferences,
    KEYCON_OT_toggle_display,
    KEYCON_PT_panel,
)


def register_keymaps():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon if wm else None
    if not kc:
        return

    km = kc.keymaps.new(name="Window", space_type="EMPTY")
    kmi = km.keymap_items.new("keycon.toggle_display", type="F8", value="PRESS", ctrl=True, shift=True)
    ADDON_KEYMAPS.append((km, kmi))


def unregister_keymaps():
    for km, kmi in ADDON_KEYMAPS:
        km.keymap_items.remove(kmi)
    ADDON_KEYMAPS.clear()


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_keymaps()


def unregister():
    STATE["running"] = False
    STATE["history"].clear()

    if STATE["timer"] and bpy.context.window_manager:
        bpy.context.window_manager.event_timer_remove(STATE["timer"])
    STATE["timer"] = None

    _remove_draw_handlers()
    unregister_keymaps()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
