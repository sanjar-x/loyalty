# Aiogram 3.x — UX-паттерны и дизайн диалогов

> Глубокое исследование UX-решений для Telegram-ботов на Aiogram 3.x

---

## Содержание

1. [Паттерны клавиатур](#1-паттерны-клавиатур)
2. [FSM-сценарии](#2-fsm-сценарии)
3. [Обработка ошибок (UX)](#3-обработка-ошибок-ux)
4. [Локализация (i18n)](#4-локализация-i18n)
5. [Медиа и контент](#5-медиа-и-контент)
6. [Паттерны взаимодействия](#6-паттерны-взаимодействия)
7. [Антипаттерны UX](#7-антипаттерны-ux)

---

## 1. Паттерны клавиатур

### 1.1 InlineKeyboardMarkup vs ReplyKeyboardMarkup

#### Когда использовать ReplyKeyboardMarkup

Reply-клавиатура располагается **вместо стандартной клавиатуры** внизу экрана. Подходит для:

- Главного меню бота
- Частых действий, доступных всегда
- Простых выборов (да/нет, выбор языка)
- Действий, не привязанных к конкретному сообщению

```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Вариант 1: Через Builder (рекомендуется)
def get_main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📦 Мои заказы")
    builder.button(text="🛒 Каталог")
    builder.button(text="💰 Баланс")
    builder.button(text="⚙️ Настройки")
    builder.button(text="❓ Помощь")
    builder.adjust(2, 2, 1)  # 2 кнопки, 2 кнопки, 1 кнопка
    return builder.as_markup(
        resize_keyboard=True,      # Подгоняет размер под кнопки
        input_field_placeholder="Выберите действие..."
    )

# Вариант 2: Статическая клавиатура
MAIN_MENU_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 Мои заказы"), KeyboardButton(text="🛒 Каталог")],
        [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="⚙️ Настройки")],
        [KeyboardButton(text="❓ Помощь")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие...",
)
```

**Специальные кнопки Reply-клавиатуры:**

```python
from aiogram.types import KeyboardButton, KeyboardButtonRequestChat

# Запрос контакта
contact_btn = KeyboardButton(text="📱 Отправить номер", request_contact=True)

# Запрос геолокации
location_btn = KeyboardButton(text="📍 Отправить местоположение", request_location=True)

# Запрос пользователя (Telegram 6.x+)
user_btn = KeyboardButton(
    text="👤 Выбрать пользователя",
    request_users=KeyboardButtonRequestUsers(request_id=1, user_is_bot=False)
)
```

#### Когда использовать InlineKeyboardMarkup

Inline-клавиатура прикрепляется **к конкретному сообщению**. Подходит для:

- Действий в контексте сообщения (лайк, удалить, подробнее)
- Пагинации и навигации по спискам
- Подтверждений действий
- Любых выборов, привязанных к контенту

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_product_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 В корзину", callback_data=f"cart:add:{product_id}")
    builder.button(text="❤️ В избранное", callback_data=f"fav:add:{product_id}")
    builder.button(text="📋 Подробнее", callback_data=f"product:detail:{product_id}")
    builder.adjust(2, 1)
    return builder.as_markup()
```

#### Сравнительная таблица

| Критерий        | ReplyKeyboard               | InlineKeyboard            |
| --------------- | --------------------------- | ------------------------- |
| Расположение    | Под полем ввода             | Под сообщением            |
| Персистентность | Остаётся до замены/удаления | Привязана к сообщению     |
| Отправляет      | Текстовое сообщение         | CallbackQuery             |
| История чата    | Засоряет чат текстом        | Чистая история            |
| Контекст        | Глобальные действия         | Действия над объектом     |
| Специальные     | Контакт, геолокация, юзер   | URL, WebApp, SwitchInline |

**Best Practice:** Используйте Reply для главного меню и постоянных действий, Inline — для всего остального.

---

### 1.2 Callback Data Factory (CallbackData)

Строковые callback_data `f"action:{id}"` — это антипаттерн. Aiogram 3.x предоставляет типизированные фабрики:

```python
from aiogram.filters.callback_data import CallbackData
from enum import IntEnum

class ProductAction(IntEnum):
    VIEW = 0
    ADD_TO_CART = 1
    FAVORITE = 2
    DELETE = 3

class ProductCallback(CallbackData, prefix="product"):
    action: ProductAction
    product_id: int
    page: int = 0  # Значение по умолчанию

class PaginationCallback(CallbackData, prefix="page"):
    entity: str       # "products", "orders", "reviews"
    page: int
    per_page: int = 10

# Создание кнопок
builder = InlineKeyboardBuilder()
builder.button(
    text="🛒 В корзину",
    callback_data=ProductCallback(
        action=ProductAction.ADD_TO_CART,
        product_id=42,
        page=1
    )
)

# Обработка — используем .filter()
@router.callback_query(ProductCallback.filter(F.action == ProductAction.ADD_TO_CART))
async def on_add_to_cart(
    callback: CallbackQuery,
    callback_data: ProductCallback,  # Автоматически распарсится
):
    product_id = callback_data.product_id
    await callback.answer(f"Товар #{product_id} добавлен в корзину!")
```

**Важно:** callback_data в Telegram ограничена **64 байтами**. Используйте короткие prefix, IntEnum вместо строк, числовые ID.

```python
# ❌ Плохо — длинный prefix, строковые значения
class BadCallback(CallbackData, prefix="product_management"):
    action: str  # "add_to_cart" = 11 символов

# ✅ Хорошо — короткий prefix, IntEnum
class GoodCallback(CallbackData, prefix="p"):
    a: int  # 0, 1, 2, 3
    id: int
```

---

### 1.3 Динамические клавиатуры с пагинацией

```python
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Sequence
from dataclasses import dataclass

class PageCallback(CallbackData, prefix="pg"):
    entity: str
    page: int

@dataclass
class PaginatedResult:
    items: Sequence
    total: int
    page: int
    per_page: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


def build_paginated_kb(
    result: PaginatedResult,
    entity: str,
    item_callback_factory: CallbackData,
    item_text_getter: callable,
    item_data_getter: callable,
    columns: int = 1,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Кнопки элементов
    for item in result.items:
        builder.button(
            text=item_text_getter(item),
            callback_data=item_data_getter(item),
        )
    builder.adjust(columns)

    # Навигационная строка
    nav_row = []
    if result.has_prev:
        nav_row.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=PageCallback(entity=entity, page=result.page - 1).pack()
        ))

    nav_row.append(InlineKeyboardButton(
        text=f"{result.page}/{result.total_pages}",
        callback_data="noop"  # Ничего не делает
    ))

    if result.has_next:
        nav_row.append(InlineKeyboardButton(
            text="Вперёд ▶️",
            callback_data=PageCallback(entity=entity, page=result.page + 1).pack()
        ))

    builder.row(*nav_row)
    return builder.as_markup()


# Использование
@router.callback_query(PageCallback.filter(F.entity == "products"))
async def on_products_page(callback: CallbackQuery, callback_data: PageCallback, repo: ProductRepo):
    result = await repo.get_paginated(page=callback_data.page, per_page=10)

    kb = build_paginated_kb(
        result=result,
        entity="products",
        item_callback_factory=ProductCallback,
        item_text_getter=lambda p: f"{p.name} — {p.price}₽",
        item_data_getter=lambda p: ProductCallback(action=ProductAction.VIEW, product_id=p.id),
        columns=1,
    )

    await callback.message.edit_text("📦 Каталог товаров:", reply_markup=kb)
    await callback.answer()
```

---

### 1.4 Паттерн навигации: назад, домой, отмена

```python
class NavCallback(CallbackData, prefix="nav"):
    to: str  # "back", "home", "cancel"
    context: str = ""  # откуда вызвано

def add_nav_buttons(builder: InlineKeyboardBuilder, show_back: bool = True, show_home: bool = True):
    """Добавляет навигационную строку к любой клавиатуре."""
    nav = []
    if show_back:
        nav.append(InlineKeyboardButton(
            text="◀️ Назад", callback_data=NavCallback(to="back").pack()
        ))
    if show_home:
        nav.append(InlineKeyboardButton(
            text="🏠 Главная", callback_data=NavCallback(to="home").pack()
        ))
    if nav:
        builder.row(*nav)

# Паттерн "хлебные крошки" — стек навигации
from aiogram.fsm.context import FSMContext

async def push_screen(state: FSMContext, screen: str):
    """Сохраняет текущий экран в стек."""
    data = await state.get_data()
    stack = data.get("nav_stack", [])
    stack.append(screen)
    await state.update_data(nav_stack=stack)

async def pop_screen(state: FSMContext) -> str | None:
    """Возвращает предыдущий экран из стека."""
    data = await state.get_data()
    stack = data.get("nav_stack", [])
    if stack:
        screen = stack.pop()
        await state.update_data(nav_stack=stack)
        return screen
    return None

@router.callback_query(NavCallback.filter(F.to == "back"))
async def on_back(callback: CallbackQuery, state: FSMContext):
    screen = await pop_screen(state)
    if screen:
        # Диспатчим на нужный экран
        await render_screen(callback.message, screen, state)
    else:
        await render_home(callback.message, state)
    await callback.answer()
```

---

## 2. FSM-сценарии

### 2.1 Линейные диалоги (анкеты, регистрация)

```python
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove

router = Router()

class RegistrationForm(StatesGroup):
    name = State()
    age = State()
    city = State()
    phone = State()
    confirm = State()

# Шаг 0: Запуск
@router.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    await state.set_state(RegistrationForm.name)
    await message.answer(
        "👋 Давайте познакомимся!\n\nКак вас зовут?",
        reply_markup=ReplyKeyboardRemove()
    )

# Шаг 1: Имя
@router.message(RegistrationForm.name, F.text)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("❌ Имя должно быть от 2 до 50 символов. Попробуйте ещё раз:")
        return  # Остаёмся в том же состоянии

    await state.update_data(name=name)
    await state.set_state(RegistrationForm.age)
    await message.answer(f"Приятно познакомиться, {name}! 🎂 Сколько вам лет?")

# Шаг 2: Возраст
@router.message(RegistrationForm.age, F.text)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите число:")
        return

    age = int(message.text)
    if age < 14 or age > 120:
        await message.answer("❌ Возраст должен быть от 14 до 120 лет:")
        return

    await state.update_data(age=age)
    await state.set_state(RegistrationForm.city)
    await message.answer("🏙 В каком городе вы находитесь?")

# Шаг 3: Город
@router.message(RegistrationForm.city, F.text)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await state.set_state(RegistrationForm.phone)

    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Отправить номер", request_contact=True)
    builder.button(text="⏩ Пропустить")
    builder.adjust(1)

    await message.answer(
        "📞 Поделитесь номером телефона или пропустите этот шаг:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# Шаг 4a: Телефон — через контакт
@router.message(RegistrationForm.phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await _show_confirmation(message, state)

# Шаг 4b: Телефон — пропуск
@router.message(RegistrationForm.phone, F.text == "⏩ Пропустить")
async def process_phone_skip(message: Message, state: FSMContext):
    await state.update_data(phone=None)
    await _show_confirmation(message, state)

# Шаг 5: Подтверждение
async def _show_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(RegistrationForm.confirm)

    phone_text = data.get("phone") or "не указан"
    text = (
        "📋 <b>Проверьте данные:</b>\n\n"
        f"👤 Имя: {data['name']}\n"
        f"🎂 Возраст: {data['age']}\n"
        f"🏙 Город: {data['city']}\n"
        f"📞 Телефон: {phone_text}\n\n"
        "Всё верно?"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="reg:confirm")
    builder.button(text="🔄 Заново", callback_data="reg:restart")
    builder.button(text="❌ Отмена", callback_data="reg:cancel")
    builder.adjust(2, 1)

    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(RegistrationForm.confirm, F.data == "reg:confirm")
async def on_confirm(callback: CallbackQuery, state: FSMContext, repo: UserRepo):
    data = await state.get_data()
    await repo.create_user(**data)
    await state.clear()
    await callback.message.edit_text("✅ Регистрация завершена! Добро пожаловать!")
    await callback.answer()
```

---

### 2.2 Ветвящиеся диалоги

```python
class OrderForm(StatesGroup):
    choose_type = State()
    # Ветка "доставка"
    delivery_address = State()
    delivery_time = State()
    # Ветка "самовывоз"
    pickup_point = State()
    # Общее
    payment_method = State()
    confirm = State()

@router.callback_query(OrderForm.choose_type, F.data == "order:delivery")
async def on_delivery(callback: CallbackQuery, state: FSMContext):
    await state.update_data(order_type="delivery")
    await state.set_state(OrderForm.delivery_address)
    await callback.message.edit_text("🏠 Введите адрес доставки:")
    await callback.answer()

@router.callback_query(OrderForm.choose_type, F.data == "order:pickup")
async def on_pickup(callback: CallbackQuery, state: FSMContext):
    await state.update_data(order_type="pickup")
    await state.set_state(OrderForm.pickup_point)

    builder = InlineKeyboardBuilder()
    builder.button(text="📍 ТЦ Мега", callback_data="pickup:1")
    builder.button(text="📍 ТЦ Галерея", callback_data="pickup:2")
    builder.button(text="📍 Центральный офис", callback_data="pickup:3")
    builder.adjust(1)

    await callback.message.edit_text(
        "Выберите точку самовывоза:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# После обеих веток — сходимся в payment_method
@router.message(OrderForm.delivery_address, F.text)
async def process_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(OrderForm.payment_method)
    await _show_payment_options(message)

@router.callback_query(OrderForm.pickup_point, F.data.startswith("pickup:"))
async def process_pickup(callback: CallbackQuery, state: FSMContext):
    point_id = int(callback.data.split(":")[1])
    await state.update_data(pickup_point_id=point_id)
    await state.set_state(OrderForm.payment_method)
    await _show_payment_options(callback.message)
    await callback.answer()
```

---

### 2.3 Отмена и возврат на предыдущий шаг

```python
from aiogram.filters import Command, StateFilter

# Глобальная отмена — работает в любом состоянии FSM
@router.message(StateFilter("*"), Command("cancel"))
@router.message(StateFilter("*"), F.text.casefold() == "отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.")
        return

    await state.clear()
    await message.answer(
        "❌ Действие отменено. Вы в главном меню.",
        reply_markup=get_main_menu_kb()
    )

# Возврат на предыдущий шаг
# Храним историю шагов в FSM data
REGISTRATION_STEPS = [
    RegistrationForm.name,
    RegistrationForm.age,
    RegistrationForm.city,
    RegistrationForm.phone,
    RegistrationForm.confirm,
]

STEP_PROMPTS = {
    RegistrationForm.name: "Как вас зовут?",
    RegistrationForm.age: "Сколько вам лет?",
    RegistrationForm.city: "В каком городе?",
    RegistrationForm.phone: "Номер телефона:",
}

@router.message(StateFilter(RegistrationForm), Command("back"))
async def cmd_back(message: Message, state: FSMContext):
    current = await state.get_state()
    try:
        idx = REGISTRATION_STEPS.index(current)
    except ValueError:
        return

    if idx == 0:
        await message.answer("Вы на первом шаге. Используйте /cancel для отмены.")
        return

    prev_state = REGISTRATION_STEPS[idx - 1]
    await state.set_state(prev_state)
    prompt = STEP_PROMPTS.get(prev_state, "Предыдущий шаг:")
    await message.answer(f"⬅️ Вернулись назад.\n\n{prompt}")
```

---

### 2.4 Timeout для незавершённых диалогов

```python
import asyncio
from aiogram.fsm.context import FSMContext

# Вариант 1: Middleware с проверкой TTL
class FSMTimeoutMiddleware(BaseMiddleware):
    def __init__(self, timeout_seconds: int = 300):  # 5 минут
        self.timeout = timeout_seconds

    async def __call__(self, handler, event, data):
        state: FSMContext = data.get("state")
        if state:
            current = await state.get_state()
            if current:
                fsm_data = await state.get_data()
                started_at = fsm_data.get("_fsm_started_at")
                now = time.time()

                if started_at and (now - started_at) > self.timeout:
                    await state.clear()
                    if isinstance(event, Message):
                        await event.answer(
                            "⏰ Время диалога истекло. Начните заново.",
                            reply_markup=get_main_menu_kb()
                        )
                    return

        return await handler(event, data)

# Вариант 2: Redis TTL при использовании RedisStorage
from aiogram.fsm.storage.redis import RedisStorage

storage = RedisStorage.from_url(
    "redis://localhost:6379/0",
    state_ttl=300,   # TTL для состояния — 5 минут
    data_ttl=600,    # TTL для данных — 10 минут
)
```

---

## 3. Обработка ошибок (UX)

### 3.1 Глобальный error handler

```python
from aiogram import Router
from aiogram.types import ErrorEvent
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.error()
async def global_error_handler(event: ErrorEvent):
    """Ловит все необработанные исключения."""
    logger.exception(
        "Unhandled error in update %s: %s",
        event.update.update_id,
        event.exception,
    )

    # Определяем, куда ответить
    user_message = None
    if event.update.message:
        user_message = event.update.message
    elif event.update.callback_query:
        await event.update.callback_query.answer(
            "😔 Произошла ошибка. Попробуйте позже.",
            show_alert=True
        )
        return

    if user_message:
        await user_message.answer(
            "😔 Что-то пошло не так. Мы уже разбираемся!\n"
            "Попробуйте ещё раз или напишите /start"
        )
```

### 3.2 Обработка неизвестных команд и сообщений

```python
# ❌ Плохо — игнорировать непонятные сообщения (пользователь не понимает, что делать)
# ❌ Плохо — отвечать "Я вас не понимаю" на каждое сообщение

# ✅ Хорошо — контекстный fallback
@router.message(StateFilter(None))  # Только вне FSM
async def fallback_handler(message: Message):
    """Обрабатывает все сообщения, не попавшие в другие хэндлеры."""
    if message.text and message.text.startswith("/"):
        await message.answer(
            "🤔 Неизвестная команда.\n"
            "Список доступных команд: /help"
        )
    else:
        await message.answer(
            "Не совсем понял вас. Воспользуйтесь меню 👇",
            reply_markup=get_main_menu_kb()
        )

# Fallback во время FSM — подсказка что делать
@router.message(RegistrationForm.age)
async def fallback_age(message: Message):
    """Если пользователь прислал не число при вводе возраста."""
    await message.answer(
        "🔢 Пожалуйста, введите ваш возраст числом.\n"
        "Например: 25\n\n"
        "Для отмены: /cancel"
    )
```

### 3.3 Паттерн дружелюбных ошибок

```python
# ✅ Правила хорошего сообщения об ошибке:
# 1. Объясните ЧТО пошло не так (коротко)
# 2. Скажите ЧТО ДЕЛАТЬ дальше
# 3. Дайте выход (кнопка, команда)

# ❌ Плохо
await message.answer("Error 500")
await message.answer("Ошибка!")
await message.answer("Произошла непредвиденная ошибка. Пожалуйста, обратитесь в службу поддержки.")

# ✅ Хорошо
await message.answer(
    "😔 Не удалось оформить заказ — сервис оплаты временно недоступен.\n\n"
    "Попробуйте через пару минут или выберите другой способ оплаты 👇",
    reply_markup=payment_methods_kb()
)
```

### 3.4 callback.answer() — обязательно!

```python
# ❌ Плохо — пользователь видит "часики" на кнопке
@router.callback_query(F.data == "action")
async def on_action(callback: CallbackQuery):
    await do_something()
    await callback.message.edit_text("Готово!")
    # Забыли callback.answer() — Telegram показывает loading 30 секунд

# ✅ Хорошо
@router.callback_query(F.data == "action")
async def on_action(callback: CallbackQuery):
    await do_something()
    await callback.message.edit_text("Готово!")
    await callback.answer()  # Убирает loading

# ✅ С уведомлением (toast)
await callback.answer("✅ Добавлено в корзину!")

# ✅ С алертом (модальное окно)
await callback.answer("⚠️ Товар закончился на складе", show_alert=True)
```

---

## 4. Локализация (i18n)

### 4.1 Fluent vs gettext

| Критерий             | Fluent                    | gettext      |
| -------------------- | ------------------------- | ------------ |
| Плюрализация         | Встроенная, мощная        | Ограниченная |
| Синтаксис            | Понятный, декларативный   | .po файлы    |
| Интеграция с aiogram | aiogram-i18n, fluentogram | aiogram-i18n |
| Сложные конструкции  | Отлично                   | Слабо        |
| Экосистема           | Молодая (Mozilla)         | Зрелая       |

**Рекомендация:** Fluent (через `fluentogram`) для новых проектов.

### 4.2 Настройка Fluent + fluentogram

```
locales/
├── ru/
│   ├── main.ftl
│   ├── errors.ftl
│   └── keyboards.ftl
├── en/
│   ├── main.ftl
│   ├── errors.ftl
│   └── keyboards.ftl
└── uz/
    ├── main.ftl
    ├── errors.ftl
    └── keyboards.ftl
```

**locales/ru/main.ftl:**

```ftl
welcome = 👋 Добро пожаловать, { $name }!
balance = 💰 Ваш баланс: { $amount } ₽
orders-count = У вас { $count ->
    [one] { $count } заказ
    [few] { $count } заказа
   *[other] { $count } заказов
}
```

**locales/en/main.ftl:**

```ftl
welcome = 👋 Welcome, { $name }!
balance = 💰 Your balance: ${ $amount }
orders-count = You have { $count ->
    [one] { $count } order
   *[other] { $count } orders
}
```

```python
from fluentogram import TranslatorHub, FluentTranslator
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

# Middleware для внедрения переводчика
class I18nMiddleware(BaseMiddleware):
    def __init__(self, hub: TranslatorHub):
        self.hub = hub

    async def __call__(self, handler, event: TelegramObject, data: dict):
        # Получаем язык пользователя (из БД или из Telegram)
        user = data.get("event_from_user")
        user_lang = "ru"  # По умолчанию

        if user:
            # Из БД (если сохранён выбор)
            repo = data.get("repo")
            if repo:
                db_user = await repo.get_user(user.id)
                if db_user and db_user.language:
                    user_lang = db_user.language
            # Fallback на язык Telegram-клиента
            elif user.language_code in ("ru", "en", "uz"):
                user_lang = user.language_code

        translator = self.hub.get_translator_by_locale(user_lang)
        data["i18n"] = translator
        data["locale"] = user_lang
        return await handler(event, data)

# Использование в хэндлерах
@router.message(Command("start"))
async def cmd_start(message: Message, i18n: FluentTranslator):
    await message.answer(
        i18n.get("welcome", name=message.from_user.first_name)
    )

@router.message(Command("balance"))
async def cmd_balance(message: Message, i18n: FluentTranslator, repo: UserRepo):
    user = await repo.get_user(message.from_user.id)
    await message.answer(
        i18n.get("balance", amount=user.balance)
    )
```

### 4.3 Смена языка пользователем

```python
class LangCallback(CallbackData, prefix="lang"):
    code: str

@router.message(Command("language"))
async def cmd_language(message: Message, i18n: FluentTranslator):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data=LangCallback(code="ru"))
    builder.button(text="🇬🇧 English", callback_data=LangCallback(code="en"))
    builder.button(text="🇺🇿 O'zbek", callback_data=LangCallback(code="uz"))
    builder.adjust(1)
    await message.answer("🌐 Выберите язык:", reply_markup=builder.as_markup())

@router.callback_query(LangCallback.filter())
async def on_language_change(callback: CallbackQuery, callback_data: LangCallback, repo: UserRepo):
    await repo.update_language(callback.from_user.id, callback_data.code)
    await callback.message.edit_text("✅ Язык изменён!")
    await callback.answer()
```

---

## 5. Медиа и контент

### 5.1 Отправка фото, видео, документов

```python
from aiogram.types import FSInputFile, URLInputFile, BufferedInputFile

# Из файловой системы
photo = FSInputFile("images/banner.jpg", filename="banner.jpg")
await message.answer_photo(photo, caption="Наш баннер")

# По URL
photo_url = URLInputFile("https://example.com/image.jpg")
await message.answer_photo(photo_url)

# Из буфера (генерация на лету)
import io
from PIL import Image

img = Image.new("RGB", (200, 200), color="red")
buffer = io.BytesIO()
img.save(buffer, format="PNG")
buffer.seek(0)

photo = BufferedInputFile(buffer.read(), filename="generated.png")
await message.answer_photo(photo)

# Переиспользование file_id (самый быстрый способ)
# Telegram кэширует файлы — при повторной отправке используйте file_id
sent = await message.answer_photo(FSInputFile("photo.jpg"))
file_id = sent.photo[-1].file_id  # Сохраняем в БД
# Потом:
await message.answer_photo(file_id)  # Мгновенная отправка
```

### 5.2 Альбомы (MediaGroup)

```python
from aiogram.types import InputMediaPhoto, InputMediaVideo

# Отправка альбома
media_group = [
    InputMediaPhoto(
        media=FSInputFile("photos/1.jpg"),
        caption="<b>Товар:</b> Кроссовки Nike\n💰 Цена: 12 990 ₽",
        parse_mode="HTML"
    ),
    InputMediaPhoto(media=FSInputFile("photos/2.jpg")),
    InputMediaPhoto(media=FSInputFile("photos/3.jpg")),
]
await message.answer_media_group(media_group)

# ⚠️ Ограничения:
# - Caption только у первого элемента (будет показана под альбомом)
# - 2-10 элементов
# - Нельзя смешивать фото и видео (но можно фото + видео через InputMediaDocument)
# - Нельзя добавить InlineKeyboard к альбому
# Решение: отправьте альбом, затем отдельное сообщение с кнопками

await message.answer_media_group(media_group)
await message.answer(
    "Выберите действие:",
    reply_markup=product_actions_kb(product_id=42)
)
```

### 5.3 Обработка входящих альбомов

```python
from aiogram import F, Router
from aiogram.types import Message
import asyncio

# Aiogram 3.x — middleware для сборки альбомов
class AlbumMiddleware(BaseMiddleware):
    """Собирает сообщения из одного альбома в список."""
    DELAY = 0.5  # Ждём полсекунды для сбора всех частей

    def __init__(self):
        self.albums: dict[str, list[Message]] = {}

    async def __call__(self, handler, event: Message, data: dict):
        if not event.media_group_id:
            return await handler(event, data)

        album_id = event.media_group_id

        if album_id not in self.albums:
            self.albums[album_id] = []
            self.albums[album_id].append(event)
            await asyncio.sleep(self.DELAY)

            data["album"] = self.albums.pop(album_id)
            return await handler(event, data)
        else:
            self.albums[album_id].append(event)
            return  # Не вызываем handler для дубликатов

# Обработчик
@router.message(F.media_group_id)
async def handle_album(message: Message, album: list[Message]):
    file_ids = []
    for msg in album:
        if msg.photo:
            file_ids.append(msg.photo[-1].file_id)
        elif msg.video:
            file_ids.append(msg.video.file_id)

    await message.answer(f"📸 Получено {len(file_ids)} файлов из альбома!")
```

### 5.4 Форматирование текста

```python
from aiogram.utils.markdown import html_decoration as hd
from aiogram.enums import ParseMode

# HTML — рекомендуется (проще экранирование, больше возможностей)
text = (
    f"<b>Заказ #{order.id}</b>\n\n"
    f"📦 Товар: {hd.quote(order.product_name)}\n"  # Экранируем пользовательский текст!
    f"💰 Сумма: <code>{order.total} ₽</code>\n"
    f"📅 Дата: {order.created_at:%d.%m.%Y}\n\n"
    f"<i>Статус: {order.status}</i>\n"
    f'<a href="{order.tracking_url}">🔗 Отследить</a>\n\n'
    f"<tg-spoiler>Промокод: {order.promo}</tg-spoiler>"
)
await message.answer(text, parse_mode=ParseMode.HTML)

# Доступные HTML-теги:
# <b>bold</b>  <i>italic</i>  <u>underline</u>  <s>strikethrough</s>
# <code>monospace</code>  <pre>pre-formatted</pre>
# <pre><code class="language-python">highlighted</code></pre>
# <a href="url">link</a>  <a href="tg://user?id=123">mention</a>
# <tg-spoiler>spoiler</tg-spoiler>
# <blockquote>quote</blockquote>  <blockquote expandable>expandable quote</blockquote>

# ⚠️ Всегда экранируйте пользовательский текст!
from html import escape
safe_text = escape(user_input)  # или hd.quote()
```

### 5.5 Длинные сообщения — разбивка

```python
from aiogram.utils.text_decorations import html_decoration

MAX_MESSAGE_LENGTH = 4096

def split_long_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Разбивает длинный текст на части, стараясь не рвать слова."""
    if len(text) <= max_length:
        return [text]

    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break

        # Ищем последний перенос строки или пробел
        split_at = text.rfind("\n", 0, max_length)
        if split_at == -1:
            split_at = text.rfind(" ", 0, max_length)
        if split_at == -1:
            split_at = max_length

        parts.append(text[:split_at])
        text = text[split_at:].lstrip()

    return parts


async def send_long_message(message: Message, text: str, **kwargs):
    """Отправляет длинное сообщение, разбивая на части."""
    parts = split_long_message(text)
    for i, part in enumerate(parts):
        if i == len(parts) - 1:
            # Клавиатуру ставим только на последнее сообщение
            await message.answer(part, **kwargs)
        else:
            await message.answer(part, parse_mode=kwargs.get("parse_mode"))
```

---

## 6. Паттерны взаимодействия

### 6.1 Onboarding нового пользователя

```python
@router.message(Command("start"))
async def cmd_start(message: Message, repo: UserRepo, state: FSMContext):
    user = await repo.get_user(message.from_user.id)

    if user:
        # Возвращающийся пользователь
        await message.answer(
            f"С возвращением, {user.name}! 👋",
            reply_markup=get_main_menu_kb()
        )
    else:
        # Новый пользователь — onboarding
        # Обработка deep link
        args = message.text.split(maxsplit=1)
        referral_code = args[1] if len(args) > 1 else None

        if referral_code:
            await state.update_data(referral_code=referral_code)

        await message.answer(
            "👋 Добро пожаловать в наш магазин!\n\n"
            "Я помогу вам:\n"
            "🛒 Найти и заказать товары\n"
            "📦 Отследить заказы\n"
            "💰 Копить и тратить бонусы\n\n"
            "Давайте начнём с регистрации!",
        )
        await state.set_state(RegistrationForm.name)
        await message.answer("Как вас зовут?")
```

### 6.2 Меню бота (BotCommand, MenuButton)

```python
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

async def set_bot_commands(bot: Bot):
    """Устанавливает команды в меню бота."""

    # Общие команды для всех пользователей
    user_commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="catalog", description="🛒 Каталог"),
        BotCommand(command="orders", description="📦 Мои заказы"),
        BotCommand(command="balance", description="💰 Баланс"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="language", description="🌐 Сменить язык"),
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # Расширенные команды для админов
    admin_commands = user_commands + [
        BotCommand(command="admin", description="⚙️ Админ-панель"),
        BotCommand(command="broadcast", description="📣 Рассылка"),
        BotCommand(command="stats", description="📊 Статистика"),
    ]
    for admin_id in config.admin_ids:
        await bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=admin_id)
        )

# Вызов при старте
async def on_startup(bot: Bot):
    await set_bot_commands(bot)

dp.startup.register(on_startup)
```

### 6.3 Deep linking

```python
from aiogram.filters import CommandStart, CommandObject
from aiogram.utils.deep_linking import create_start_link, decode_payload

# Генерация deep link
link = await create_start_link(bot, payload="ref_12345", encode=True)
# Результат: https://t.me/your_bot?start=cmVmXzEyMzQ1

# Обработка
@router.message(CommandStart(deep_link=True))
async def cmd_start_deep(message: Message, command: CommandObject, repo: UserRepo):
    payload = command.args
    if not payload:
        return

    # Обработка реферальной ссылки
    if payload.startswith("ref_"):
        referrer_id = int(payload.split("_")[1])
        await repo.save_referral(
            user_id=message.from_user.id,
            referrer_id=referrer_id
        )
        await message.answer("🎉 Вы перешли по реферальной ссылке! Бонус начислен.")

    # Обработка ссылки на товар
    elif payload.startswith("product_"):
        product_id = int(payload.split("_")[1])
        product = await repo.get_product(product_id)
        if product:
            await show_product(message, product)
```

### 6.4 Рассылки и уведомления

```python
import asyncio
import logging

logger = logging.getLogger(__name__)

async def broadcast(
    bot: Bot,
    user_ids: list[int],
    text: str,
    reply_markup=None,
    batch_size: int = 25,
    delay: float = 1.0,
) -> tuple[int, int]:
    """
    Рассылка с учётом лимитов Telegram API:
    - Не более 30 сообщений в секунду
    - Не более 20 сообщений в минуту в один чат
    """
    success = 0
    failed = 0

    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i + batch_size]

        for user_id in batch:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=reply_markup,
                )
                success += 1
            except TelegramForbiddenError:
                # Пользователь заблокировал бота
                failed += 1
                logger.info("User %s blocked the bot", user_id)
            except TelegramRetryAfter as e:
                # Rate limit — ждём
                await asyncio.sleep(e.retry_after)
                await bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)
                success += 1
            except Exception:
                failed += 1
                logger.exception("Failed to send to %s", user_id)

        await asyncio.sleep(delay)

    return success, failed
```

### 6.5 Web App интеграция

```python
from aiogram.types import WebAppInfo, InlineKeyboardButton, MenuButtonWebApp

# Кнопка WebApp в Inline-клавиатуре
builder = InlineKeyboardBuilder()
builder.button(
    text="🌐 Открыть каталог",
    web_app=WebAppInfo(url="https://shop.example.com/catalog")
)

# WebApp в главном меню бота
async def set_webapp_menu(bot: Bot):
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🛒 Магазин",
            web_app=WebAppInfo(url="https://shop.example.com")
        )
    )

# Получение данных из WebApp
from aiogram.types import Message

@router.message(F.web_app_data)
async def handle_webapp_data(message: Message, repo: OrderRepo):
    """Получаем данные из WebApp (корзина, заказ и т.д.)."""
    import json
    data = json.loads(message.web_app_data.data)

    if data.get("action") == "create_order":
        order = await repo.create_order(
            user_id=message.from_user.id,
            items=data["items"],
            address=data["address"],
        )
        await message.answer(f"✅ Заказ #{order.id} оформлен!")
```

---

## 7. Антипаттерны UX

### 7.1 Что раздражает пользователей

#### ❌ Избыточные подтверждения

```python
# ❌ ПЛОХО — подтверждение на каждый чих
"Вы уверены, что хотите посмотреть каталог?"
"Подтвердите просмотр товара"
"Вы точно хотите вернуться в меню?"

# ✅ ХОРОШО — подтверждение только для необратимых действий
# Удаление аккаунта, отмена заказа, оплата — да
# Навигация, просмотр, добавление в избранное — нет

@router.callback_query(F.data.startswith("order:cancel:"))
async def on_cancel_order(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[2])
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Да, отменить", callback_data=f"order:cancel_confirm:{order_id}")
    builder.button(text="◀️ Нет, вернуться", callback_data=f"order:view:{order_id}")
    builder.adjust(1)
    await callback.message.edit_text(
        "⚠️ Отменить заказ? Это действие нельзя отменить.",
        reply_markup=builder.as_markup()
    )
```

#### ❌ Слишком глубокая вложенность меню

```python
# ❌ ПЛОХО — 5+ уровней вложенности
# Главная → Настройки → Уведомления → Email → Частота → Выбор

# ✅ ХОРОШО — максимум 3 уровня
# Главная → Настройки → [все опции на одном экране с toggle-кнопками]

# Паттерн "плоское меню с toggle"
@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, repo: UserRepo):
    user = await repo.get_user(callback.from_user.id)
    builder = InlineKeyboardBuilder()

    # Toggle-кнопки — всё на одном экране
    notif_icon = "🔔" if user.notifications_on else "🔕"
    builder.button(
        text=f"{notif_icon} Уведомления",
        callback_data="settings:toggle:notifications"
    )

    email_icon = "📧" if user.email_on else "📭"
    builder.button(
        text=f"{email_icon} Email-рассылка",
        callback_data="settings:toggle:email"
    )

    lang_names = {"ru": "🇷🇺 RU", "en": "🇬🇧 EN", "uz": "🇺🇿 UZ"}
    builder.button(
        text=f"🌐 Язык: {lang_names[user.language]}",
        callback_data="settings:language"
    )

    builder.button(text="◀️ Назад", callback_data="home")
    builder.adjust(1)

    await callback.message.edit_text("⚙️ Настройки:", reply_markup=builder.as_markup())
    await callback.answer()
```

#### ❌ Молчание бота

```python
# ❌ ПЛОХО — бот не отвечает при длительных операциях
@router.message(Command("report"))
async def cmd_report(message: Message):
    report = await generate_heavy_report()  # 10 секунд
    await message.answer_document(report)

# ✅ ХОРОШО — показать индикатор действия
from aiogram.utils.chat_action import ChatActionSender

@router.message(Command("report"))
async def cmd_report(message: Message, bot: Bot):
    status_msg = await message.answer("⏳ Генерирую отчёт...")
    async with ChatActionSender.upload_document(
        chat_id=message.chat.id, bot=bot
    ):
        report = await generate_heavy_report()
    await status_msg.delete()
    await message.answer_document(report)
```

#### ❌ Неинформативные кнопки

```python
# ❌ ПЛОХО
builder.button(text="Ок", callback_data="ok")
builder.button(text="Нет", callback_data="no")
builder.button(text="Далее", callback_data="next")

# ✅ ХОРОШО — кнопка говорит что произойдёт
builder.button(text="✅ Оформить заказ", callback_data="order:create")
builder.button(text="🗑 Очистить корзину", callback_data="cart:clear")
builder.button(text="📦 К списку товаров", callback_data="catalog:page:1")
```

#### ❌ Отсутствие обратной связи

```python
# ❌ ПЛОХО — пользователь нажал кнопку и ничего не произошло
@router.callback_query(F.data == "fav:add")
async def add_to_fav(callback: CallbackQuery):
    await repo.add_favorite(callback.from_user.id, product_id)
    # Нет ответа пользователю

# ✅ ХОРОШО — моментальная обратная связь
@router.callback_query(F.data == "fav:add")
async def add_to_fav(callback: CallbackQuery):
    await repo.add_favorite(callback.from_user.id, product_id)
    await callback.answer("❤️ Добавлено в избранное!")
    # Или обновить кнопку:
    # Заменить "❤️ В избранное" на "💔 Убрать из избранного"
```

#### ❌ Стена текста

```python
# ❌ ПЛОХО — огромное сообщение с инструкциями
await message.answer(
    "Добро пожаловать! Наш бот позволяет вам просматривать каталог товаров, "
    "оформлять заказы, отслеживать доставку, копить бонусные баллы, "
    "приглашать друзей по реферальной программе, оставлять отзывы, "
    "связываться с поддержкой, настраивать уведомления..."  # ещё 500 символов
)

# ✅ ХОРОШО — краткое приветствие + кнопки для навигации
await message.answer(
    "👋 Добро пожаловать!\n\n"
    "Выберите, что вас интересует 👇",
    reply_markup=get_main_menu_kb()
)
```

---

### 7.2 Чеклист хорошего UX бота

| #   | Правило                                       | Проверка                     |
| --- | --------------------------------------------- | ---------------------------- |
| 1   | Каждая кнопка имеет `callback.answer()`       | Нет "часиков"                |
| 2   | Fallback-хэндлер для неизвестных сообщений    | Бот не молчит                |
| 3   | `/cancel` работает в любом FSM-состоянии      | Выход всегда                 |
| 4   | Длительные операции — ChatAction + статус     | Пользователь ждёт не вслепую |
| 5   | Максимум 3 уровня вложенности меню            | Навигация понятна            |
| 6   | Подтверждение только для необратимых действий | Не раздражает                |
| 7   | Кнопки описывают результат, не процесс        | "Оформить заказ" vs "Ок"     |
| 8   | Пользовательский ввод экранируется            | Нет XSS через HTML           |
| 9   | Ошибки объясняют что делать дальше            | Нет тупиков                  |
| 10  | Бот помнит контекст в рамках диалога          | FSM data не теряется         |
| 11  | Меню бота (`BotCommand`) настроено            | Быстрый доступ               |
| 12  | Reply-клавиатура с `resize_keyboard=True`     | Не занимает пол-экрана       |

---

## Источники

- [Aiogram 3.x Documentation](https://docs.aiogram.dev/en/latest/)
- [Aiogram GitHub](https://github.com/aiogram/aiogram)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Telegram Bot UX Guidelines](https://core.telegram.org/bots#how-do-i-create-a-bot)
- [Fluentogram](https://github.com/Arustinal/fluentogram)
- [aiogram-dialog](https://github.com/Tishka17/aiogram_dialog)
- [Fluent Syntax Guide](https://projectfluent.org/fluent/guide/)
