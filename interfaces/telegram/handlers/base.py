from aiogram import Router, types
from aiogram.filters import Command
from interfaces.telegram.keypads import get_control_keyboard
from config.logger import logger

router = Router(name="base_router")

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Start command welcoming the authorized administrator."""
    logger.info(f"Start command triggered by {message.from_user.id}")
    welcome_text = (
        "🤖 **Xush kelibsiz, Boshliq (Central AI Boss)!**\n\n"
        "Men sizning kompyuteringizni boshqarish, asinxron agentlarni orkestratsiya qilish "
        "va tizim telemetryasini monitoring qilishga mo'ljallangan **Markaziy Sun'iy Intellekt Brain** tizimiman.\n\n"
        "Quyidagi boshqaruv paneli orqali tezkor amallarni bajarishingiz yoki istalgan buyruqni "
        "oddiy o'zbek/ingliz tilida matn ko'rinishida yuborishingiz mumkin:"
    )
    await message.answer(
        text=welcome_text,
        reply_markup=get_control_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Provides usage details for the operating system."""
    help_text = (
        "❓ **Boshqaruv Qo'llanmasi:**\n\n"
        "• `/start` - Boshqaruv panelini ko'rsatish.\n"
        "• `/help` - Ushbu qo'llanma.\n\n"
        "💬 **Matnli buyruqlar:**\n"
        "Siz tizimga oddiy matnli ko'rsatmalar bera olasiz. Brain orqali asinxron ravishda "
        "kerakli agentlar ishga tushadi:\n"
        "_\"Kompyuterimdan Google Chrome'ni och va yangi tab ochib 'FastAPI' deb qidir\"_\n"
        "_\"d:\\my_folder papkasidagi barcha loglarni tozalab tashla\"_\n\n"
        "⚠️ **Xavfsizlik:**\n"
        "Har qanday xavfli tizim yoki o'chirish buyruqlari bajarilishidan oldin bot panelida "
        "**Tasdiqlash (HITL)** tugmasi paydo bo'ladi."
    )
    await message.answer(text=help_text, parse_mode="Markdown")
