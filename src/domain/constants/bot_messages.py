GROUP_GREETING = (
    "Hi everyone, let's get talking!\n"
    "\n"
    "I'll jump into conversations when:\n"
    "- Someone replies to my messages\n"
    "- Someone mentions me by username\n"
    '- Someone says the trigger word: "{trigger_word}"\n'
    "\n"
    "Commands:\n"
    "/settrigger@{username} <word> - Set a custom trigger word (admins only)\n"
    "/trigger@{username} - Check the current trigger word\n"
    "/setlanguage@{username} <language> - Set the bot's language (admins only)\n"
    "/language@{username} - Check the current language\n"
    "/setpersona@{username} <text> - Set a custom persona (admins only)\n"
    "/persona@{username} - Check the current persona\n"
    "/health@{username} - Show system health info (admins only)"
)

RATE_LIMITED = "I'm tired! Ping me later..."

TRIGGER_SET = "Trigger word updated to: {trigger_word}"
TRIGGER_CURRENT = "Current trigger word: {trigger_word}"
TRIGGER_NOT_SET = "No trigger word is set for this group."
TRIGGER_USAGE = (
    "Usage: /settrigger@{username} <word>\nExample: /settrigger@{username} bot"
)
TRIGGER_UPDATE_FAILED = "Failed to update trigger word. Please try again later."

LANGUAGE_SET = "Language updated to: {language}"
LANGUAGE_CURRENT = "Current language: {language}"
LANGUAGE_NOT_SET = "No language is set for this group."
LANGUAGE_USAGE = "Usage: /setlanguage@{username} <language>\nExample: /setlanguage@{username} English"
LANGUAGE_UPDATE_FAILED = "Failed to update language. Please try again later."

PERSONA_SET = "Persona updated."
PERSONA_CLEARED = "Persona cleared."
PERSONA_CURRENT = "Current persona:\n\n{persona}"
PERSONA_NOT_SET = "No persona is set for this group."
PERSONA_TOO_LONG = "Persona is too long. Maximum {maxchars} characters allowed."
PERSONA_UPDATE_FAILED = "Failed to update persona. Please try again later."

NOT_GROUP_ADMIN = "This command can only be used by group administrators."
GROUP_NOT_FOUND = "Group not found. Please try again later."
