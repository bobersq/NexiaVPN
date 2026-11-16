# NexiaVPN

Современный VPN-клиент для Windows с поддержкой VLESS, VMess, Trojan и Shadowsocks.

![NexiaVPN Screenshot](assets/screenshot.png)

## Возможности

- 🚀 **Реальное подключение** через Xray-core
- 🌐 **4 протокола**: VLESS, VMess, Trojan, Shadowsocks
- 📋 **Вставка ссылок**: поддержка `vless://`, `vmess://`, `trojan://`, `ss://`
- 📡 **Измерение пинга** в реальном времени
- 🌍 **Определение страны** сервера (GeoIP)
- 🎨 **Тёмный UI** с синe-фиолетовой темой
- 💾 **Автосохранение** серверов
- 🔒 **Безопасное хранение** конфиденциальных данных
- ⚙️ **Гибкие настройки**: DNS, порты, маршрутизация

## Быстрый старт

### Требования
- Windows 10 / 11 (x64)
- Python 3.10+

### Запуск

```bat
start.bat
```

При первом запуске:
1. Автоматически установятся Python-зависимости
2. Откроется диалог загрузки Xray-core
3. Запустится NexiaVPN

### Добавление сервера

1. Нажмите **«+ Добавить»**
2. Вставьте VPN-ссылку(и):
   ```
   vless://uuid@server.com:443?type=ws&security=tls#My Server
   vmess://eyJhZGQiOiJzZXJ2ZXIuY29tIiwicG9ydCI6NDQzfQ==
   trojan://password@server.com:443
   ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@server.com:8388#SS Server
   ```
3. Нажмите **«Добавить»**

### Подключение

- Дважды кликните по серверу **или**
- Выберите сервер и нажмите кнопку **CONNECT**

## Настройка прокси в браузере

После подключения настройте прокси:
- **HTTP/HTTPS**: `127.0.0.1:10808`
- **SOCKS5**: `127.0.0.1:10809`

Или используйте браузерное расширение (SwitchyOmega и т.д.)

## Структура проекта

```
nexiavpn/
├── main.py              # Точка входа
├── requirements.txt     # Python-зависимости
├── start.bat            # Запуск
├── build.bat            # Сборка EXE
├── create_icon.py       # Генерация иконки
├── core/
│   ├── engine.py        # Управление Xray-процессом
│   ├── link_parser.py   # Парсинг VPN-ссылок
│   ├── server_storage.py # Хранение серверов
│   ├── setup_manager.py # Автоустановка зависимостей
│   └── xray_config.py   # Генерация конфига Xray
├── ui/
│   ├── main_window.py   # Главное окно
│   ├── widgets.py       # Кастомные виджеты
│   ├── add_server_dialog.py
│   ├── settings_dialog.py
│   └── stylesheet.py    # CSS-стили
├── utils/
│   ├── geo.py           # GeoIP lookup
│   └── logger.py        # Безопасный логгер
├── config/              # Создаётся при запуске
│   ├── servers.json     # Список серверов
│   ├── settings.json    # Настройки
│   └── xray_config.json # Текущий конфиг Xray
├── bin/                 # Создаётся при установке
│   └── xray.exe         # Xray-core (скачивается автоматически)
├── assets/
│   └── icon.png
└── logs/                # Логи (без паролей и ссылок)
```

## Сборка EXE

```bat
build.bat
```

Создаёт `dist/NexiaVPN.exe` — готовый исполняемый файл.

## Безопасность

- VPN-ссылки хранятся в обфусцированном виде в `config/servers.json`
- Пароли и UUID **никогда не записываются** в логи
- Загружаемые файлы — только из официального репозитория XTLS/Xray-core
- Windows Defender не отключается

## Поддерживаемые параметры ссылок

### VLESS
`vless://uuid@host:port?type=ws&security=tls&sni=host&path=/ws&fp=chrome#name`

Параметры `security`: `tls`, `reality`, `none`

### VMess
`vmess://` + base64(JSON с полями: add, port, id, aid, net, type, host, path, tls, sni)

### Trojan
`trojan://password@host:port?sni=host&fp=chrome#name`

### Shadowsocks
`ss://base64(method:password)@host:port#name`

Поддерживаемые шифры: `aes-128-gcm`, `aes-256-gcm`, `chacha20-ietf-poly1305`

## Режимы маршрутизации

| Режим | Описание |
|-------|----------|
| **Только прокси** | Трафик идёт через VPN только из настроенного браузера/приложения |
| **Глобальный** | Весь трафик через VPN |
| **Обход CN** | Китайские IP идут напрямую, остальное через VPN |

## Лицензия

MIT License — используйте свободно.

---

> ⚠️ **Важно**: NexiaVPN не обходит блокировки автоматически в системном масштабе.
> После подключения вручную настройте прокси в браузере или приложениях.
> Для системного туннелирования требуются права администратора и TUN-режим.
