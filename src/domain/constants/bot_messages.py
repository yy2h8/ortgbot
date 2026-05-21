GROUP_GREETING = (
    "Ну привет, давайте общаться!\n"
    "\n"
    "Я буду вам отвечать, когда:\n"
    "- Кто-то отвечает на мои сообщения\n"
    "- Кто-то упоминает меня по юзернейму\n"
    '- Кто-то говорит триггерное слово: "{trigger_word}"\n'
    "\n"
    "Команды для администраторов:\n"
    "/settrigger@{username} <word> - Установить триггер\n"
    "/setlanguage@{username} <language> - Установить язык бота\n"
    "/setpersona@{username} <text> - Установить персону\n"
    "/health@{username} - Показать информацию о состоянии системы\n"
    "\n"
    "Общие команды:\n"
    "/trigger@{username} - Показать триггер\n"
    "/language@{username} - Показать язык бота\n"
    "/persona@{username} - Показать персону"
)

RATE_LIMITED = "Я устал! Пингните меня позже..."

TRIGGER_SET = "Триггер обновлен на: {trigger_word}"
TRIGGER_CURRENT = "Текущий триггер: {trigger_word}"
TRIGGER_NOT_SET = "Триггер для этой группы не установлен!"
TRIGGER_USAGE = (
    "Использование: /settrigger@{username} <word>\nПример: /settrigger@{username} ботяра"
)
TRIGGER_UPDATE_FAILED = "Не удалось обновить триггер, попробуйте позже?"

LANGUAGE_SET = "Язык обновлен на: {language}"
LANGUAGE_CURRENT = "Текущий язык: {language}"
LANGUAGE_NOT_SET = "Язык для этой группы не установлен!"
LANGUAGE_USAGE = "Использование: /setlanguage@{username} <language>\nПример: /setlanguage@{username} Russian"
LANGUAGE_UPDATE_FAILED = "Не удалось обновить язык, попробуйте позже?"

PERSONA_SET = "Персона обновлена"
PERSONA_CLEARED = "Персона очищена"
PERSONA_CURRENT = "Текущая персона: {persona}"
PERSONA_NOT_SET = "Персона для этой группы не установлена!"
PERSONA_TOO_LONG = "Персона слишком длинная. Максимум {maxchars} символов"
PERSONA_UPDATE_FAILED = "Не удалось обновить персону, попробуйте позже?"

NOT_GROUP_ADMIN = "Эта команда может использоваться только администраторами группы"
GROUP_NOT_FOUND = "Группа не найдена, попробуйте позже?"
