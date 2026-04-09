Мы создали image_backend для обработки изображений в отдельном микросервисе чтобы не нагружать основной сервер обработкой изображений
и реализовал систему Direct to S3

Посмотри Flow загрузки изображений продуктов
Сейчас при загрузке fronted сделал POST запрос на image_backend на эндпоинт /api/media/upload
Payload: {contentType: "image/jpeg", filename: "reebok.jpg"}
и получил 201 Response:
{
    "storageObjectId": "019d594c-db0d-72c2-9a58-4ab4a6ec53b9",
    "presignedUrl": "https://t3.storage.dev/loyality/raw_uploads/media/02acb8b1-34bc-4503-81cc-e6896068dcb9/upload_raw.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=tid_dllVENag_SshDmdCCmkPKqOeekqRmUSKbuLgRPbQac_QfZsfKb%2F20260404%2Fauto%2Fs3%2Faws4_request&X-Amz-Date=20260404T162142Z&X-Amz-Expires=300&X-Amz-SignedHeaders=content-type%3Bhost&X-Amz-Signature=12548788a6a39c4ba1521e64da2ee348d648556abbb0ddac1f390f2f5cb4d18f",
    "expiresIn": 300
}

После сделал POST запрос на Bucket по /api/media/s3-upload
Payload:
file: (binary)
presignedUrl: https://t3.storage.dev/loyality/raw_uploads/media/02acb8b1-34bc-4503-81cc-e6896068dcb9/upload_raw.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=tid_dllVENag_SshDmdCCmkPKqOeekqRmUSKbuLgRPbQac_QfZsfKb%2F20260404%2Fauto%2Fs3%2Faws4_request&X-Amz-Date=20260404T162142Z&X-Amz-Expires=300&X-Amz-SignedHeaders=content-type%3Bhost&X-Amz-Signature=12548788a6a39c4ba1521e64da2ee348d648556abbb0ddac1f390f2f5cb4d18f
Получил 200 Response: {"ok":true}

После уведомил image_backend сделав POST запрос по /api/media/019d594c-db0d-72c2-9a58-4ab4a6ec53b9/confirm
Получл 202 Response {"storageObjectId":"019d594c-db0d-72c2-9a58-4ab4a6ec53b9","status":"processing"}

И 28 раз сделал GET запрос по /api/media/019d594c-db0d-72c2-9a58-4ab4a6ec53b9
и каждый раз получил 200 Response : {
    "storageObjectId": "019d594c-db0d-72c2-9a58-4ab4a6ec53b9",
    "status": "PROCESSING",
    "url": null,
    "contentType": "image/jpeg",
    "sizeBytes": 0,
    "variants": [],
    "createdAt": "2026-04-04T16:21:42.506913Z"
}

И в логике есть несколько проблем и задач
1) Многократный GET запрос это spam можно получиь 429 Нужно реализовать SSE
2) Пока изображение загружается в S3 у изображения должен стоять жёлты статус а не лоадер который ограничивает просмотр в ImageViewer
3) После загрузки в S3 у нас вместо старого blob должен стоять url в S3 чтобы у нас было хотя бы необработанное изображения в случае если изображение не получится обработать в Image backend мы могли отправить в Backend необработанное оригинальное изображение. Public URL https://loyality.t3.tigrisfiles.io а и адресс изображения их пример будет вот таким https://loyality.t3.tigrisfiles.io/raw_uploads/media/02acb8b1-34bc-4503-81cc-e6896068dcb9/upload_raw.jpg
4) При сообщении об успешной обработки заменить URL Raw изображения на URL обработанного изображения


Почему Кнопка сохранить не работает изучи @backend_openapi.json API Документацию и страницу @frontend/admin/src/app/admin/products/add/ Нужно правильно реализовать весь функционал
