# Генерация пакета документации

#### Генерируем документацию для указанной партии:

```
curl -X GET --header "Accept: */*"
--header "Content-Type: application/json"
--header "Authorization: AccessToken 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"
--header "X-User-Authorization: Basic bG9naW46cGFzc3dvcmQ="
"{host}/1.0/forms/15/zip-all"
```

Response body:

PDF file
