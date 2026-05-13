# Формирование партий из новых заказов

#### Формируем партии из 3х заказов с разными типами отправления. В итоге формируется 3 партии - каждая соотвествующего типа:

```
curl -X POST --header "Content-Type: application/json"
--header "Accept: application/json;charset=UTF-8"
--header "Authorization: AccessToken 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"
--header "X-User-Authorization: Basic bG9naW46cGFzc3dvcmQ="
-d "[1657697,1657662,1657698]"
"{host}/1.0/user/shipment?sending-date=2016-08-22"
```

Response body:

```json
{
  "batches": [
    {
      "batch-name": "15",
      "batch-status": "CREATED",
      "batch-status-date": "2016-08-19T08:11:12.386Z",
      "delivery-notice-payment-method": "PAID_RECIPIENT",
      "list-number-date": "2016-08-22",
      "mail-category": "ORDINARY",
      "mail-category-text": "Обыкновенное",
      "mail-type": "POSTAL_PARCEL",
      "mail-type-text": "Посылка НЕСТАНДАРТНАЯ",
      "payment-method": "CASHLESS",
      "postoffice-code": "101000",
      "postoffice-name": "ЦВПП 101000",
      "shipment-count": 1,
      "shipping-notice-type": "SIMPLE",
      "transport-type": "SURFACE"
    },
    {
      "batch-name": "16",
      "batch-status": "CREATED",
      "batch-status-date": "2016-08-19T08:11:12.387Z",
      "delivery-notice-payment-method": "PAID_RECIPIENT",
      "list-number-date": "2016-08-22",
      "mail-category": "WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY",
      "mail-category-text": "С ОЦ и НП",
      "mail-type": "POSTAL_PARCEL",
      "mail-type-text": "Посылка НЕСТАНДАРТНАЯ",
      "payment-method": "CASHLESS",
      "postoffice-code": "101000",
      "postoffice-name": "ЦВПП 101000",
      "shipment-count": 1,
      "shipping-notice-type": "SIMPLE",
      "transport-type": "SURFACE"
    },
    {
      "batch-name": "17",
      "batch-status": "CREATED",
      "batch-status-date": "2016-08-19T08:11:12.382Z",
      "delivery-notice-payment-method": "PAID_RECIPIENT",
      "list-number-date": "2016-08-22",
      "mail-category": "WITH_DECLARED_VALUE",
      "mail-category-text": "С ОЦ",
      "mail-type": "POSTAL_PARCEL",
      "mail-type-text": "Посылка НЕСТАНДАРТНАЯ",
      "payment-method": "CASHLESS",
      "postoffice-code": "101000",
      "postoffice-name": "ЦВПП 101000",
      "shipment-count": 1,
      "shipping-notice-type": "SIMPLE",
      "transport-type": "SURFACE"
    }
  ],
  "result-ids": [
    1657697,
    1657662,
    1657698
  ]
}
```
