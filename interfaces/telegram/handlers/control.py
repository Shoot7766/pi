import os
from aiogram import Router, F, types
from tools.registry import tool_registry
from core.security import security_guard
from core.memory.relational import RelationalMemory
from config.logger import logger

router = Router(name="control_router")

@router.callback_query(F.data == "btn_screenshot")
async def handle_screenshot_btn(callback: types.CallbackQuery):
    """Captures and sends current system display screen."""
    await callback.message.answer("📸 Ekran rasmga olinmoqda (Screenshot)...")
    await callback.answer()

    screenshotter = tool_registry.get_tool("system_screenshotter")
    output_path = "d:/ai_robot/pi/storage/screenshot.jpg"
    
    try:
        # Call safe screenshot logic
        res = await screenshotter.capture_screen(output_path)
        
        if os.path.exists(output_path):
            photo = types.FSInputFile(output_path)
            await callback.message.reply_photo(photo=photo, caption="🖥 Boshliq, joriy ekran ko'rinishi:")
        else:
            await callback.message.answer(f"❌ Rasmni yuklashda xatolik: {res}")
    except Exception as e:
        logger.error(f"Screenshot button trigger failed: {e}")
        await callback.message.answer(f"❌ Xatolik yuz berdi: {e}")

@router.callback_query(F.data == "btn_sysinfo")
async def handle_sysinfo_btn(callback: types.CallbackQuery):
    """Retrieves OS telemetry using safe shell command execution."""
    await callback.message.answer("📊 Tizim ma'lumotlari yig'ilmoqda...")
    await callback.answer()

    shell = tool_registry.get_tool("safe_shell_runner")
    
    # In Windows use ver/systeminfo, else standard uname/uptime
    cmd = "systeminfo" if os.name == "nt" else "uname -a && uptime"
    # To prevent systeminfo from taking too long, we filter down on Windows
    if os.name == "nt":
        cmd = "hostname && ver"

    try:
        output = await shell.execute_command(cmd)
        await callback.message.answer(f"📋 **Tizim Tafsilotlari:**\n\n```\n{output}\n```", parse_mode="Markdown")
    except Exception as e:
        await callback.message.answer(f"❌ Telemetriya yig'ishda xatolik: {e}")

@router.callback_query(F.data == "btn_pending_hitl")
async def handle_pending_hitl(callback: types.CallbackQuery):
    """Lists current outstanding security requests in the queue."""
    pending = security_guard.get_pending_requests()
    await callback.answer()

    if not pending:
        await callback.message.answer("✅ Hozircha kutilayotgan tasdiqlovchi buyruqlar yo'q.")
        return

    text = "⏳ **Ruxsat kutilayotgan buyruqlar ro'yxati:**\n\n"
    for item in pending:
        text += f"• ID: `{item['request_id']}`\n  Harakat: _{item['prompt']}_\n\n"
    
    await callback.message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data.startswith("hitl_approve_"))
async def handle_hitl_approve(callback: types.CallbackQuery):
    """Approve a pending execution process."""
    request_id = callback.data.split("hitl_approve_")[1]
    security_guard.approve_request(request_id)
    
    await callback.answer("Buyruq bajarilishiga ruxsat berildi! ✅", show_alert=True)
    await callback.message.edit_text(
        text=f"{callback.message.text}\n\n🟢 **TASDIQLANDI (Approved)** by Boss.",
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("hitl_deny_"))
async def handle_hitl_deny(callback: types.CallbackQuery):
    """Deny a pending execution process."""
    request_id = callback.data.split("hitl_deny_")[1]
    security_guard.deny_request(request_id)
    
    await callback.answer("Buyruq bekor qilindi! ❌", show_alert=True)
    await callback.message.edit_text(
        text=f"{callback.message.text}\n\n🔴 **RAD ETILDI (Denied)** by Boss.",
        parse_mode="Markdown"
    )
