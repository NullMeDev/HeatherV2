from telegram import InlineKeyboardButton, InlineKeyboardMarkup

__all__ = [
    'create_batch_control_keyboard',
    'create_card_button',
    'create_main_menu',
    'create_single_gates_menu',
    'create_batch_menu',
    'create_back_button',
    'create_settings_menu',
    'create_tools_menu',
    'create_ai_menu',
    'create_help_menu',
    'create_paired_menu',
]


def create_batch_control_keyboard(session_id: str, is_paused: bool = False) -> InlineKeyboardMarkup:
    """Create inline keyboard for batch control (pause/resume/stop)"""
    if is_paused:
        keyboard = [
            [
                InlineKeyboardButton("▶️ Resume", callback_data=f"batch_resume_{session_id}"),
                InlineKeyboardButton("⏹️ Stop", callback_data=f"batch_stop_{session_id}"),
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("⏸️ Pause", callback_data=f"batch_pause_{session_id}"),
                InlineKeyboardButton("⏹️ Stop", callback_data=f"batch_stop_{session_id}"),
            ]
        ]
    return InlineKeyboardMarkup(keyboard)


def create_card_button(card_input: str) -> InlineKeyboardMarkup:
    """Create a copy button for valid card format"""
    try:
        parts = card_input.split('|')
        if len(parts) == 4 and parts[0].isdigit() and len(parts[0]) >= 13:
            keyboard = [
                [InlineKeyboardButton("📋 Copy Card", callback_data=f"copy_{card_input}")]
            ]
            return InlineKeyboardMarkup(keyboard)
    except (ValueError, KeyError, AttributeError) as e:
        pass
    return None


def create_main_menu() -> InlineKeyboardMarkup:
    """Main menu with categories"""
    keyboard = [
        [
            InlineKeyboardButton("💳 SINGLE", callback_data="cat_single"),
            InlineKeyboardButton("📦 BATCH", callback_data="cat_batch"),
        ],
        [
            InlineKeyboardButton("🔧 TOOLS", callback_data="cat_tools"),
            InlineKeyboardButton("🔗 PAIRED", callback_data="cat_paired"),
        ],
        [
            InlineKeyboardButton("🤖 AI", callback_data="cat_ai"),
            InlineKeyboardButton("⚙️ SETTINGS", callback_data="cat_settings"),
        ],
        [
            InlineKeyboardButton("❓ HELP", callback_data="cat_help"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_single_gates_menu() -> InlineKeyboardMarkup:
    """Single card gates submenu"""
    keyboard = [
        [
            InlineKeyboardButton("🔄 ALL AUTH", callback_data="all_auth"),
            InlineKeyboardButton("🔄 ALL CHARGE", callback_data="all_charge"),
        ],
        [
            InlineKeyboardButton("🔐 Auth Gates", callback_data="single_auth"),
            InlineKeyboardButton("💰 Charge Gates", callback_data="single_charge"),
        ],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_batch_menu() -> InlineKeyboardMarkup:
    """Batch processing submenu"""
    keyboard = [
        [
            InlineKeyboardButton("🔐 Auth Batch", callback_data="batch_auth"),
            InlineKeyboardButton("💰 Charge Batch", callback_data="batch_charge"),
        ],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_back_button(callback: str = "back_main") -> InlineKeyboardMarkup:
    """Create a single back button"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data=callback)]])


def create_settings_menu() -> InlineKeyboardMarkup:
    """Settings submenu"""
    keyboard = [
        [
            InlineKeyboardButton("📡 Check Proxy", callback_data="set_proxy"),
            InlineKeyboardButton("📊 View Metrics", callback_data="set_metrics"),
        ],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_tools_menu() -> InlineKeyboardMarkup:
    """Tools submenu"""
    keyboard = [
        [InlineKeyboardButton("🔙 BACK", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_ai_menu() -> InlineKeyboardMarkup:
    """AI assistants submenu"""
    keyboard = [
        [InlineKeyboardButton("🔙 BACK", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_help_menu() -> InlineKeyboardMarkup:
    """Help submenu"""
    keyboard = [
        [InlineKeyboardButton("🔙 BACK", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_paired_menu() -> InlineKeyboardMarkup:
    """Paired check submenu"""
    keyboard = [
        [InlineKeyboardButton("🔙 BACK", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)
