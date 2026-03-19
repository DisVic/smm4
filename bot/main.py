# Terra Danza Bot - Чат-бот для интерактивной энциклопедии мирового танца
# Функции: информирование о проекте, FAQ, сбор заявок на участие, связь с командой

import asyncio
import logging
import re
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID, FAQ_DATA, LEAD_QUESTIONS
from database import Database

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ==================== ИНИЦИАЛИЗАЦИЯ ====================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()
router = Router()
dp.include_router(router)

# ==================== СОСТОЯНИЯ FSM ====================

class LeadForm(StatesGroup):
    # Состояния для квалификации лида
    name = State()
    company = State()
    service = State()
    budget = State()
    contact = State()

class OperatorMode(StatesGroup):
    # Состояние режима общения с оператором
    chatting = State()

# ==================== КЛАВИАТУРЫ ====================

def get_main_keyboard():
    # Главное меню
    buttons = [
        [InlineKeyboardButton(text="🌍 О проекте", callback_data="menu_services")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="menu_faq")],
        [InlineKeyboardButton(text="📝 Оставить заявку", callback_data="menu_lead")],
        [InlineKeyboardButton(text="👨‍💼 Связаться с командой", callback_data="menu_operator")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_faq_keyboard():
    # Клавиатура FAQ
    buttons = []
    for key, data in FAQ_DATA.items():
        buttons.append([InlineKeyboardButton(
            text=data["question"][:30] + "..." if len(data["question"]) > 30 else data["question"],
            callback_data=f"faq_{key}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_services_keyboard():
    # Клавиатура возможностей проекта
    buttons = [
        [InlineKeyboardButton(text="🗺️ Карта танцев мира", callback_data="service_1")],
        [InlineKeyboardButton(text="📚 История танцев", callback_data="service_2")],
        [InlineKeyboardButton(text="🎓 Курсы и мастер-классы", callback_data="service_3")],
        [InlineKeyboardButton(text="🎬 Медиатека", callback_data="service_4")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="menu_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard():
    # Клавиатура отмены
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_lead")]
    ])

def get_options_keyboard(options: list):
    # Клавиатура с вариантами выбора
    buttons = [[InlineKeyboardButton(text=opt, callback_data=f"option_{opt}")] for opt in options]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_lead")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_keyboard():
    # Кнопка назад
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="menu_back")]
    ])

def get_end_chat_keyboard():
    # Кнопка завершения чата с оператором
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить чат", callback_data="end_operator_chat")]
    ])

# ==================== ХЕНДЛЕРЫ КОМАНД ====================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    # Обработка команды /start
    user = message.from_user
    
    # Сохраняем пользователя в БД
    db.add_or_update_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Очищаем состояние
    await state.clear()
    
    # Логируем
    db.log_message(user.id, "command", "/start")
    logger.info(f"Пользователь {user.id} ({user.username}) запустил бота")
    
    # Отправляем приветствие
    welcome_text = (
        f"👋 Привет, {user.first_name or 'дорогой друг'}!\n\n"
        "Добро пожаловать в Terra Danza! 💃🕺\n\n"
        "Я — виртуальный помощник интерактивной энциклопедии мирового танца.\n\n"
        "Я помогу вам:\n"
        "• Узнать о проекте и возможностях\n"
        "• Получить ответы на вопросы\n"
        "• Оставить заявку на участие\n"
        "• Связаться с командой проекта\n\n"
        "Выберите действие в меню:"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@router.message(Command("help"))
async def cmd_help(message: Message):
    # Обработка команды /help
    help_text = (
        "📖 Справка по использованию бота\n\n"
        "Доступные команды:\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/stats - Статистика (только для админа)\n\n"
        "Используйте кнопки меню для навигации."
    )
    await message.answer(help_text)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    # Статистика бота (только для админа)
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return
    
    stats = db.get_stats()
    stats_text = (
        "📊 Статистика бота\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"📝 Всего заявок: {stats['total_leads']}\n"
        f"🆕 Новых заявок: {stats['new_leads']}\n"
        f"⏳ Ожидают ответа оператора: {stats['pending_requests']}"
    )
    await message.answer(stats_text)

# ==================== ХЕНДЛЕРЫ ГЛАВНОГО МЕНЮ ====================

@router.callback_query(F.data == "menu_back")
async def menu_back(callback: CallbackQuery, state: FSMContext):
    # Возврат в главное меню
    await state.clear()
    await callback.message.edit_text(
        "Главное меню. Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "menu_services")
async def menu_services(callback: CallbackQuery):
    # Меню возможностей проекта
    services_text = (
        "🌍 Terra Danza — возможности\n\n"
        "• Интерактивная карта танцев мира\n"
        "• История танцевальных направлений\n"
        "• Видео и аудиоматериалы\n"
        "• Статьи о культуре народов\n"
        "• Образовательные курсы\n\n"
        "Выберите раздел для подробностей:"
    )
    await callback.message.edit_text(services_text, reply_markup=get_services_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("service_"))
async def service_detail(callback: CallbackQuery):
    # Детали раздела
    service_id = callback.data.split("_")[1]
    services_info = {
        "1": (
            "🗺️ Интерактивная карта танцев мира\n\n"
            "Исследуйте танцевальные традиции разных стран:\n"
            "• Географическая привязка танцев\n"
            "• Фильтрация по регионам и эпохам\n"
            "• Фото, видео, аудио материалы\n"
            "• Исторические справки\n\n"
            "Путешествуйте по миру танцев!"
        ),
        "2": (
            "📚 История танцевальных направлений\n\n"
            "Погрузитесь в историю:\n"
            "• Хронология развития танца\n"
            "• От древности до современности\n"
            "• Персоналии: хореографы, танцоры\n"
            "• Культурный контекст\n\n"
            "Узнайте, как танцы меняли мир!"
        ),
        "3": (
            "🎓 Курсы и мастер-классы\n\n"
            "Образовательные возможности:\n"
            "• Мини-курсы по истории танцев\n"
            "• Мастер-классы от хореографов\n"
            "• Лекции о культуре народов\n"
            "• Онлайн-экскурсии по музеям\n\n"
            "Следите за анонсами в канале!"
        ),
        "4": (
            "🎬 Медиатека\n\n"
            "Коллекция материалов:\n"
            "• Видеозаписи выступлений\n"
            "• Аудиозаписи народной музыки\n"
            "• Фотогалереи костюмов\n"
            "• Документальные фильмы\n\n"
            "Погрузитесь в атмосферу танца!"
        )
    }
    
    text = services_info.get(service_id, "Раздел не найден")
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "menu_faq")
async def menu_faq(callback: CallbackQuery):
    # Меню FAQ
    await callback.message.edit_text(
        "❓ Часто задаваемые вопросы\n\nВыберите вопрос:",
        reply_markup=get_faq_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("faq_"))
async def faq_answer(callback: CallbackQuery):
    # Ответ на FAQ вопрос
    faq_key = callback.data.split("_")[1]
    
    if faq_key in FAQ_DATA:
        answer = FAQ_DATA[faq_key]["answer"]
        question = FAQ_DATA[faq_key]["question"]
        
        # Логируем просмотр FAQ
        db.log_message(callback.from_user.id, "faq_view", question)
        
        await callback.message.edit_text(
            f"❓ {question}\n\n{answer}",
            reply_markup=get_back_keyboard()
        )
    
    await callback.answer()

# ==================== ХЕНДЛЕРЫ КВАЛИФИКАЦИИ ЛИДОВ ====================

@router.callback_query(F.data == "menu_lead")
async def start_lead_form(callback: CallbackQuery, state: FSMContext):
    # Начало формы заявки
    user = callback.from_user
    
    # Логируем
    db.log_message(user.id, "action", "Начал заполнение заявки")
    logger.info(f"Пользователь {user.id} начал заполнение заявки")
    
    await callback.message.edit_text(
        "📝 Заявка на участие\n\n"
        "Ответьте на несколько вопросов, и мы свяжемся с вами!\n\n"
        "Вопрос 1/5:\nКак вас зовут?",
        reply_markup=get_cancel_keyboard()
    )
    
    await state.set_state(LeadForm.name)
    await callback.answer()

@router.message(LeadForm.name)
async def process_name(message: Message, state: FSMContext):
    # Обработка имени
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer("Имя должно содержать минимум 2 символа. Попробуйте ещё раз:")
        return
    
    await state.update_data(name=name)
    db.log_message(message.from_user.id, "lead_form", f"Имя: {name}")
    
    await message.answer(
        "Вопрос 2/5:\nКто вы? (танцор, преподаватель, исследователь...)",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(LeadForm.company)

@router.message(LeadForm.company)
async def process_background(message: Message, state: FSMContext):
    # Обработка информации о пользователе
    background = message.text.strip()
    
    await state.update_data(company=background)
    db.log_message(message.from_user.id, "lead_form", f"Статус: {background}")
    
    await message.answer(
        "Вопрос 3/5:\nЧто вас интересует в Terra Danza?",
        reply_markup=get_options_keyboard(LEAD_QUESTIONS[2]["options"])
    )
    await state.set_state(LeadForm.service)

@router.callback_query(StateFilter(LeadForm.service), F.data.startswith("option_"))
async def process_interest(callback: CallbackQuery, state: FSMContext):
    # Обработка выбора интереса
    interest = callback.data.replace("option_", "")
    
    await state.update_data(service=interest)
    db.log_message(callback.from_user.id, "lead_form", f"Интерес: {interest}")
    
    await callback.message.edit_text(
        "Вопрос 4/5:\nКакие танцевальные традиции вас интересуют?",
        reply_markup=get_options_keyboard(LEAD_QUESTIONS[3]["options"])
    )
    await state.set_state(LeadForm.budget)
    await callback.answer()

@router.callback_query(StateFilter(LeadForm.budget), F.data.startswith("option_"))
async def process_region(callback: CallbackQuery, state: FSMContext):
    # Обработка выбора региона
    region = callback.data.replace("option_", "")
    
    await state.update_data(budget=region)
    db.log_message(callback.from_user.id, "lead_form", f"Регион: {region}")
    
    await callback.message.edit_text(
        "Вопрос 5/5:\nУкажите контакт для связи (телефон или email):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(LeadForm.contact)
    await callback.answer()

@router.message(LeadForm.contact)
async def process_contact(message: Message, state: FSMContext):
    # Обработка контакта и сохранение анкеты
    contact = message.text.strip()
    
    # Валидация: телефон или email
    phone_pattern = r'^[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}$'
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not (re.match(phone_pattern, contact) or re.match(email_pattern, contact)):
        await message.answer(
            "Неверный формат. Введите корректный телефон или email:\n"
            "Примеры: +79991234567 или email@example.com",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Получаем все данные
    data = await state.get_data()
    data['contact'] = contact
    
    # Сохраняем в БД
    user = message.from_user
    success = db.save_lead(user.id, data)
    
    if success:
        # Логируем
        db.log_message(user.id, "lead_form", f"Контакт: {contact}")
        logger.info(f"Заявка от {user.id} сохранена: {data}")
        
        # Уведомление админу
        try:
            admin_text = (
                f"🔔 Новая заявка в Terra Danza!\n\n"
                f"👤 Имя: {data.get('name')}\n"
                f"🎭 Статус: {data.get('company')}\n"
                f"💡 Интерес: {data.get('service')}\n"
                f"🌍 Регион: {data.get('budget')}\n"
                f"📞 Контакт: {data.get('contact')}\n\n"
                f"Telegram: @{user.username or user.id}"
            )
            await bot.send_message(ADMIN_ID, admin_text)
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу: {e}")
        
        await message.answer(
            "✅ Спасибо! Ваша заявка принята.\n\n"
            "Команда Terra Danza свяжется с вами в ближайшее время.\n\n"
            "Вы можете вернуться в главное меню:",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "❌ Произошла ошибка при сохранении. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data == "cancel_lead")
async def cancel_lead(callback: CallbackQuery, state: FSMContext):
    # Отмена заполнения заявки
    await state.clear()
    db.log_message(callback.from_user.id, "action", "Отменил заполнение заявки")
    
    await callback.message.edit_text(
        "Заполнение заявки отменено.\n\nГлавное меню:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

# ==================== ХЕНДЛЕРЫ ОПЕРАТОРА ====================

@router.callback_query(F.data == "menu_operator")
async def request_operator(callback: CallbackQuery, state: FSMContext):
    # Запрос связи с командой проекта
    user = callback.from_user
    
    # Создаём запрос в БД
    request_id = db.create_operator_request(user.id)
    
    # Уведомление админу
    try:
        admin_text = (
            f"👨‍💼 Запрос на связь с командой Terra Danza\n\n"
            f"Пользователь: {user.first_name} (@{user.username or user.id})\n"
            f"ID: {user.id}\n"
            f"Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        await bot.send_message(ADMIN_ID, admin_text)
    except Exception as e:
        logger.error(f"Не удалось уведомить админа: {e}")
    
    # Логируем
    db.log_message(user.id, "operator_request", "Запрос связи с командой")
    logger.info(f"Пользователь {user.id} запросил связь с командой")
    
    await callback.message.edit_text(
        "👨‍💼 Связь с командой проекта\n\n"
        "Мы получили ваш запрос и скоро ответим.\n"
        "Вы можете писать сообщения прямо сюда.\n\n"
        "Нажмите «Завершить чат», когда закончите.",
        reply_markup=get_end_chat_keyboard()
    )
    
    await state.set_state(OperatorMode.chatting)
    await callback.answer()

@router.message(OperatorMode.chatting)
async def forward_to_admin(message: Message, state: FSMContext):
    # Пересылка сообщения пользователя команде проекта
    user = message.from_user
    
    try:
        # Пересылаем сообщение админу
        forward_text = (
            f"📩 Сообщение от @{user.username or user.id} ({user.first_name}):\n\n"
            f"{message.text}"
        )
        await bot.send_message(ADMIN_ID, forward_text)
        
        # Логируем
        db.log_message(user.id, "operator_chat", message.text)
        
        await message.answer("✅ Сообщение отправлено команде проекта.")
    except Exception as e:
        logger.error(f"Ошибка пересылки: {e}")
        await message.answer("❌ Не удалось отправить сообщение.")

@router.callback_query(F.data == "end_operator_chat", OperatorMode.chatting)
async def end_operator_chat(callback: CallbackQuery, state: FSMContext):
    # Завершение чата с оператором
    user = callback.from_user
    
    # Логируем
    db.log_message(user.id, "operator_chat", "Завершил чат с оператором")
    
    try:
        await bot.send_message(ADMIN_ID, f"Пользователь @{user.username or user.id} завершил чат.")
    except:
        pass
    
    await state.clear()
    
    await callback.message.edit_text(
        "Чат с оператором завершён.\n\nГлавное меню:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

# ==================== ОБРАБОТКА ОШИБОК ====================

@router.message()
async def handle_unknown_message(message: Message, state: FSMContext):
    # Обработка неизвестных сообщений
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer(
            "Я не понимаю это сообщение. Используйте кнопки меню или команду /start",
            reply_markup=get_main_keyboard()
        )
    else:
        logger.warning(f"Необработанное сообщение в состоянии {current_state}: {message.text}")

@router.callback_query()
async def handle_unknown_callback(callback: CallbackQuery):
    # Обработка неизвестных callback-запросов
    logger.warning(f"Неизвестный callback: {callback.data}")
    await callback.answer("Неизвестная команда", show_alert=True)

# ==================== ЗАПУСК БОТА ====================

async def main():
    # Главная функция запуска бота
    logger.info("Запуск бота...")
    
    # Удаляем вебхуки если есть
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем поллинг
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")