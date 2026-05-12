# Подготовка партии к приему в ОПС и отправка электронной формы Ф103 (checkin)

```
curl -X POST --header "Content-Type: application/json"
--header "Accept: application/json;charset=UTF-8"
--header "Authorization: AccessToken 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"
--header "X-User-Authorization: Basic bG9naW46cGFzc3dvcmQ="
"{host}/1.0/batch/15/checkin"
```

Response body:

```json
{}
```
