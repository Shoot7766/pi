from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_control_keyboard() -> InlineKeyboardMarkup:
    """Returns the main interactive desktop control keypad."""
    buttons = [
        [
            InlineKeyboardButton(text="📸 Ekran Rasm (Screenshot)", callback_data="btn_screenshot"),
            InlineKeyboardButton(text="📊 Tizim Holati (SysInfo)", callback_data="btn_sysinfo")
        ],
        [
            InlineKeyboardButton(text="⏳ Kutilayotgan Tasdiqlar (HITL)", callback_data="btn_pending_hitl"),
            InlineKeyboardButton(text="🧹 Kechki Tarixni Tozalash", callback_data="btn_clear_history")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_hitl_keyboard(request_id: str) -> InlineKeyboardMarkup:
    """Returns HITL Verification keyboard for security approvals."""
    buttons = [
        [
            InlineKeyboardButton(text="Tasdiqlash (Approve) ✅", callback_data=f"hitl_approve_{request_id}"),
            InlineKeyboardButton(text="Rad Etish (Deny) ❌", callback_data=f"hitl_deny_{request_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
