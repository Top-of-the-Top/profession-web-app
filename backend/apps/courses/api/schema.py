SCHEMA_DETAIL = {
    "type": "object",
    "properties": {"detail": {"type": "string"}},
}

SCHEMA_VALIDATION = {
    "type": "object",
    "description": "Ошибка валидации полей (DRF): ключи — имена полей, значения — списки сообщений; либо общее поле detail.",
    "additionalProperties": True,
}
