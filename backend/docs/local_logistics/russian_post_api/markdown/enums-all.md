
---

### Тип адреса

| Значение | Описание |
|----------|----------|
| DEFAULT | Стандартный (улица, дом, квартира) |
| PO_BOX | Абонентский ящик |
| DEMAND | До востребования |
| UNIT | Для военных частей |

---

### Категория партии

| Значение | Описание |
|----------|----------|
| SIMPLE | Простое |
| ORDERED | Заказное |
| ORDINARY | Обыкновенное |
| WITH_DECLARED_VALUE | С объявленной ценностью |
| WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | С объявленной ценностью и наложенным платежом |
| WITH_DECLARED_VALUE_AND_COMPULSORY_PAYMENT | С объявленной ценностью и обязательным платежом |
| WITH_DECLARED_VALUE_AND_COMPULSORY_PAYMENT | С объявленной ценностью и обязательным платежом |
| WITH_COMPULSORY_PAYMENT | С обязательным платежом |
| COMBINED | Комбинированное |

---

### Статусы партии

| Значение | Описание |
|----------|----------|
| CREATED | Партия создана |
| FROZEN | Партия в процессе приема, редактирование запрещено |
| ACCEPTED | Партия принята в отделении связи |
| SENT | По заказам в партии существуют данные в сервисе трекинга |
| ARCHIVED | Партия находится в архиве |

---

### Категория вложения

| Значение | Описание |
|----------|----------|
| GIFT | Подарок |
| DOCUMENT | Документы |
| SALE_OF_GOODS | Продажа товара |
| COMMERCIAL_SAMPLE | Коммерческий образец |
| OTHER | Прочее |

---

### Тип конверта

| Значение | Описание |
|----------|----------|
| C4 | 229мм x 324мм |
| C5 | 162мм x 229мм |
| C6 | 114мм x 162мм |
| DL | 110мм x 220мм |
| A6 | 105мм x 148мм |
| A7 | 74мм x 105мм |
| OX | Стикер ЗОО X6 (99 x 105 мм) |
| OA | Стикер ЗОО А6 (105 x 148,5 мм) |

---

### Атрибут операции из трекинга

| Значение | Описание |
|----------|----------|
| UNKNOWN | Атрибут операции не определен |
| FOREIGN_ACCEPTING | Прием иностранного отправления |
| SINGLE_ACCEPTING | Единичный |
| PARTIAL_ACCEPTING | Партионный |
| PARTIAL_ACCEPTING_REMOTE | Партионный электронно |
| GIVING_COMMON | Случай операции "Вручение" зарубежного отправления, когда код операции и аттрибута операции, получаемый в ответе, равен 0, т.е. мы не в состоянии по описанию операции "Вручение" точно определить было ли отправление получено адресатом или отправителем, а также как оно было получено, через почтомат или нет. |
| GIVING_RECIPIENT | Вручение адресату |
| GIVING_SENDER | Вручение отправителю |
| GIVING_RECIPIENT_IN_PO | Выдано адресату через почтомат |
| GIVING_SENDER_IN_PO | Выдано отправителю через почтомат |
| GIVING_RECIPIENT_REMOTE | Адресату электронно |
| GIVING_RECIPIENT_POSTMAN | Адресату почтальоном |
| GIVING_SENDER_POSTMAN | Отправителю почтальоном |
| GIVING_RECIPIENT_COURIER | Адресату курьером |
| GIVING_SENDER_COURIER | Отправителю курьером |
| GIVING_RECIPIENT_CONTROL | Адресату с контролем ответа |
| GIVING_RECIPIENT_CONTROL_POSTMAN | Адресату с контролем ответа почтальоном |
| GIVING_RECIPIENT_CONTROL_COURIER | Адресату с контролем ответа курьером |
| RETURNING_BY_EXPIRED_STORING | Истек срок хранения |
| RETURNING_BY_SENDER_REQUEST | Заявление отправителя |
| RETURNING_BY_RECEPIENT_ABSENCE | Отсутствие адресата по указанному адресу |
| RETURNING_BY_RECEPIENT_REJECT | Отказ адресата |
| RETURNING_BY_RECEPIENT_DEATH | Смерть адресата |
| RETURNING_BY_UNREADABLE_ADDRESS | Невозможно прочесть адрес адресата |
| RETURNING_BY_CUSTOM | Возврат таможни |
| RETURNING_BY_UNKNOWN_RECEPIENT | Адресат, абонирующий абонементный почтовый шкаф, не указан или указан неправильно |
| RETURNING_BY_OTHER_REASONS | Иные обстоятельства |
| RETURNING_BY_WRONG_ADRESS | Неверный адрес |
| DELIVERING_BY_CLIENT_REQUEST | По заявлению пользователя |
| DELIVERING_TO_NEW_ADDRESS | Выбытие адресата по новому адресу |
| DELIVERING_BY_ROUTER | Засылка |
| LOST | Утрачено |
| CONFISCATED | Изъято |
| SKIPPING_BY_ERROR | Засылка |
| SKIPPING_BY_CUSTOM | Решение таможни |
| UNDELIVERED | Доставка по указанному адресу не осуществляется |
| POSTE_RESTANTE_STORING | До востребования |
| STORING_IN_BOX | На абонементный ящик |
| TEMPORAL_STORING | Установленный срок хранения |
| ADDITIONAL_STORING | Продление срока хранения по заявлению адресата |
| CUSTOM_HOLDING | Продление срока выпуска таможней |
| UNASSIGNED | Нероздано |
| UNCLAIMED | Невостребовано |
| PROHIBITED | Содержимое запрещено к пересылке |
| SORTING | Сортировка |
| SENT | Покинуло место приёма |
| ARRIVED | Прибыло в место вручения |
| DELIVERED_TO_SORTING | Прибыло в сортировочный центр |
| SORTED | Покинуло сортировочный центр |
| DELIVERED_TO_EXCHANGE_HUB | Прибыло в место международного обмена |
| PROCESSED_BY_EXCHANGE_HUB | Покинуло место международного обмена |
| DELIVERED_TO_HUB | Прибыло в место транзита |
| LEAVED_HUB | Покинуло место транзита |
| DELIVERED_TO_PO | Прибыло в почтомат |
| EXPIRED_PO_STORING | Истекает срок хранения в почтомате |
| FORWARDED | Переадресовано в почтомат |
| GET | Изъято из почтомата |
| ARRIVED_IN_RUSSIA | Прибыло на территорию РФ |
| ARRIVED_IN_PARCELS_CENTER | Прибыло в Центр выдачи посылок |
| GIVEN_TO_COURIER | Передано курьеру |
| GIVEN_FOR_REMOTE | Доставлено для вручения электронно |
| DELIVERED_HYBRID | Прибыло в ЦГП |
| GIVEN_TO_POSTMAN | Передано почтальону |
| GIVEN_FOR_BOXROOM | Передача в кладовую хранения |
| LEFT_POSTOFFICE | Покинуло место возврата/досыла |
| SPECIFY_ADDRESS | Уточнение адреса |
| EXPECTING_COURIER_DELIVERY | Ожидает курьерской доставки |
| PROLONG_STORAGE_DATE | Продление срока хранения |
| NOTIFICATION_SENT | Направлено извещение |
| NOTIFICATION_RECEIVED | Доставлено извещение |
| POCHTOMAT_ORDERED | Доставка в почтомат заказана |
| POSTMAN_ORDERED | Доставка почтальоном заказана |
| COURIER_ORDERED | Курьерская доставка заказана |
| IMPORTED | Импорт международной почты |
| EXPORTED | Экспорт международной почты |
| ACCEPTED_BY_CUSTOM | Принято таможней |
| FAILED_BY_TEMPORAL_ABSENCE_OF_RECEPIENT | Временное отсутствие адресата |
| FAILED_BY_DELAYING_REQUEST | Доставка отложена по просьбе адресата |
| FAILED_BY_UNFILLED_ADDRESS | Неполный адрес |
| FAILED_BY_INVALID_ADDRESS | Неправильный адрес |
| FAILED_BY_RECEPIENT_LEAVING | Адресат выбыл |
| FAILED_BY_RECEPINT_REJECT | Отказ от получения |
| UNOVERCAMING_FAIL | Обстоятельства непреодолимой силы |
| FAILED_WITH_ANOTHER_REASON | Иная |
| WAITING_RECEPIENT_IN_OFFICE | Адресат заберет отправление сам |
| RECEPIENT_NOT_FOUND | Нет адресата |
| TECHNICALLY_FAILED | По техническим причинам |
| FAILED_BY_EXPIRATION_TIME | v |
| REGISTERED | Регистрация отправки |
| CUSTOM_LEGALIZED | Выпущено таможней |
| LEGALIZED | Выпущено таможней |
| CANCELED_LEGLIZATION | Возвращено таможней |
| PROCESSED_BY_CUSTOM | Осмотрено таможней |
| REJECTED_BY_CUSTOM | Отказ в выпуске |
| PASSED_WITH_CUSTOM_NOTIFY | Направлено с таможенным уведомлением |
| PASSED_WITH_CUSTOM_TAX | Направлено с обязательной уплатой таможенных платежей |
| DELIGATED | Передача на временное хранение |
| DESTROYED | Уничтожение |
| ACCOUNTED | Передача вложения на баланс |
| LOSS_REGISTERED | Утрата зарегистрирована |
| CUSTOM_DUTY_RECEIVED | Таможенные платежи поступили |
| DM_REGISTERED | Регистрация |
| DM_DELIVERED | Доставка |
| DM_ABSENCE_POSTBOX | Недоставка |
| DM_ABSENCE_ADDRESS | Недоставка |
| DM_WRONG_POSTOFFICE_INDEX | Недоставка |
| DM_WRONG_ADDRESS | Недоставка |
| TEMPORARY_STORING_ARRIVED | Поступление на временное хранение |
| CUSTOM_STORING_PROLONGED | Продление срока выпуска таможней |
| CUSTOM_STORING_PROLONGED_1 | Запрещенные вложение |
| CUSTOM_STORING_PROLONGED_2 | Импортируемые вложения являются предметом ограничений - Несоответствующая/отсутствующая лицензия |
| CUSTOM_STORING_PROLONGED_3 | Несоответствующий/отсутствующий сертификат о происхождении груза |
| CUSTOM_STORING_PROLONGED_4 | Несоответствующая/отсутствующая таможенная декларация |
| CUSTOM_STORING_PROLONGED_5 | Контакт с клиентом для запроса информации невозможен |
| CUSTOM_STORING_PROLONGED_6 | Некомплектная поставка |
| CUSTOM_STORING_PROLONGED_7 | Передано в таможенный орган |
| CUSTOM_STORING_PROLONGED_8 | Экспортируемые вложения являются предметом ограничений - Несоответствующая/отсутствующая лицензия |
| CUSTOM_STORING_PROLONGED_9 | Неполная/некорректная документация, ожидается дополнительная документация |
| OPENED | Вскрытие |
| CANCELED_BY_SENDER_DEFAULT | Отмена операции по требованию отправителя |
| CANCELED_BY_SENDER | Отмена операции по требованию отправителя |
| CANCELED_BY_OPERATOR | Отмена операции из-за ошибки оператора |
| ID_ASSIGNED | Присвоен идентификатор |
| ELECTRONIC_REGISTRATION_RECEIVED | Получена электронная регистрация |
| REGISTRATION_PASSAGE_IN_MMPO | Регистрация прохождения в ММПО |
| SRM_DISPATCH | Отправка SRM |
| TRANSPORT_ARRIVED | Транспорт прибыл |
| ACCEPTED | Бронирование подтверждено |
| ASSIGNED_TO_LOAD_PLAN | Включено в план погрузки |
| REMOVED_FROM_LOAD_PLAN | Исключено из плана погрузки |
| TRANSPORT_LEG_COMPLETED | Транспортный участок завершен |
| DELIVERED | Доставлено |
| MAIL_AT_DESTINATION | Почта в месте назначения |
| UPLIFTED | Погружено на борт |
| EN_ROUTE | В пути |
| MAIL_ARRIVED_AT_CARRIER_FACILITY | Почта поступила на склад перевозчика |
| TRANSFER | Перегрузка |
| HANDOVER_DELIVERED | Передано другому перевозчику |
| HANDOVER_RECEIVED | Получено от другого перевозчика |
| LOADED | Погружено |
| NOT_LOADED | Не погружено |
| OFFLOADED | Выгружено |
| RECEIVED | Принято к перевозке |
| RETURNED | Возвращено |
| APO_RECEIPT | Принято к перевозке |
| FORWARD_TO_CARRIER | Передано перевозчику |
| RECEIVED_DESIGNATED_OPERATOR | Получено назначенным оператором |
| PROCESSING_DESIGNATED_POSTAL_OPERATOR | Обработка назначенным оператором |
| ELECTRONIC_NOTIFICATION_UPLOADED | Электронное уведомление загружено |
| UNDELIVERABLE_SHIPMENT_TYPE | Не подлежащий доставке вид почтового отправления |
| EXCEEDING_WEIGHT_LIMIT | Превышение предельного веса, подлежащее доставке |
| EXCEEDING_OVERALL_DIMENSION | Превышение габаритных размеров, подлежащее доставке |
| DEFECTIVE_SHIPMENT | Дефектное почтовое отправление |
| CUSTOMS_NOTIFICATION_ENCLOSED | Наличие Таможенного уведомления |
| AGREEMENT_EXCHANGE_COD_SHIPMENT_NOT_ENCLOSED | Отсутствие Соглашения об обмене почтовыми отправлениями с наложенным платежом |
| RETURNED_SHIPMENT | Возвращенное почтовое отправление |
| EXCESS_COD_AMOUNT_CHARGED_AT_HOME | Превышение суммы наложенного платежа, подлежащей взиманию на дому |
| INCORRECT_DOCUMENTATION_OR_LACK_THEREOF | Неверно оформленные бланки или их отсутствие |
| INCLUDED_IN_TARIFF | Включена в тариф |
| CHARGEABLE | Платная |
| PREPAID | Предоплаченная |
| PRE_FORMALIZATION | Предварительное оформление |
| INCORRECT_UNREADABLE_INCOMPLETE_ADDRESS | Неправильный/нечитаемый/неполный адрес |
| AT_SENDER_REQUEST | По требованию отправителя |
| RETAINED_INCORRECT_DISPATCH | Засыл отправления |
| REGISTRATION | Регистрация |
| PRELIMINARY_DECISION | Предварительное решение "выпуск разрешен" |
| RETAINED_CUSTOM_WITHOUT_INSPECTION | Отказ в выпуске товаров. Требуется предъявление таможенному органу без осмотра |
| RETAINED_CUSTOM_WITH_INSPECTION | Отказ в выпуске товаров. Требуется предъявление таможенному органу с осмотром |
| REFUSAL_OF_REGISTRATION | Отказ в регистрации |
| GOODS_NOT_SHOWN | Отказ в выпуске. Товары не предъявлены |
| DATA_FROM_TRAIDING_PLAFORM_RECIVED | Данные от торговой площадки получены |
| RELEASED_BY_CUSTOMS | Выпуск разрешен |
| REJECTED_BY_CUSTOMS | Отказ в выпуске |
| PAYMENTS_PAID | Платежи уплачены |
| PAYMENT_AMOUNT_WITHHELD | Сумма платежа удержана УО |
| PAYMENT_AMOUNT_DEBITED | Сумма платежа списана ФТС |
| PAYMENT_AMOUNT_FOR_WITHHELD | Сумма платежа для удержания УО |
| PAYMENT_AMOUNT_WITHHELD_COMPLETELY | Сумма платежа удержана УО полностью |
| PAYMENT_AMOUNT_CALCULATED | Сумма платежа рассчитана УО |
| ADDRESSEE_NOT_AVAILABLE | Временное отсутствие адресата |
| ADDRESSEE_REQUESTED_LATE_DELIVERY | Доставка отложена по просьбе адресата |
| INCOMPLETE_ADDRESS | Неполный адрес |
| UNREADABLE_INCORRECT_INCOMPLETE_ADDRESS | Неправильный/нечитаемый/неполный адрес |
| SECOND_ATTEMPT_ADDRESSEE_MOVED | Адресат выбыл |
| ITEM_REFUSED_BY_ADDRESSEE | Адресат отказался от отправления |
| FORCE_MAJEURE | Форс-мажор/непредвиденные обстоятельства |
| OTHER | Иная |
| ADDRESSEE_REQUEST_OWN_PICK_UP | Адресат заберет отправление сам |
| ADDRESSEE_CANNOT_BE_LOCATED | Адресат не доступен |
| DUE_TO_TECHNICAL_DIFFICULTIES | Неудачная доставка |
| STORAGE_PERIOD_EXPIRED | Истек срок хранения в почтомате |
| SECOND_ATTEMPT_SENDER_REQUEST | По требованию отправителя |
| ITEM_DEMAGED_AND_OR_MISSING_CONTENS | Отправление повреждено и/или без вложения |
| AWAITING_PAYMENT | В ожидании оплаты сбора |
| MOVED_ADDRESSEE | Адресат переехал |
| SECOND_ATTEMPT_ADDRESSEE_HAS_P_O_BOX | У адресата есть абонентский ящик |
| SECOND_ATTEMPT_NO_HOME_DELIVERY | Нет доставки на дом |
| NOT_MEET_CUSTOMS_REQUIREMENTS | Не отвечает таможенным требованиям |
| SECOND_ATTEMPT_INCORRECT_DOCUMENTATION | Неполные/недостаточные/неверные документы |
| IMPOSSIBLE_CONTACT | Невозможно связаться с клиентом |
| SECOND_ATTEMPT_ADDRESSEE_ON_STRIKE | Адресат бастует |
| SECOND_ATTEMPT_PROHIBITED_ARTICLES | Запрещенные вложения – отправление не доставлено |
| IMPORTATION_RESTRICTED | Отказ в импорте – запрещенные вложения |
| DISPATCH_INCORRECT | Засыл отправления |
| ADDRESSEE_DECEASE | За смертью получателя |
| SECOND_ATTEMPT_LOCAL_HOLIDAY | Национальный праздник |
| ITEM_LOST | Утрата |
| DELIVERY_PERMITTED | Вручение разрешено |
| ACCEPTANCE_REJECTED | Отказ в приеме |
| ELECTRONIC_NOTIFICATION_REFUSED | Отказ от отправки электронного уведомления получателем |
| ID_ASSIGNMENT_CANCELLED | Присвоение идентификатора отменено |
| SHIPMENT_ALREADY_DELIVERED | Отправление уже вручено |
| REAPPLICATION | Заявка на продление срока хранения получена повторно |
| LATER_24_HOURS_BEFORE_COMPLETION | Заявка на продление срока хранения подана позже, чем за 24 часа окончания нормативного срока хранения |
| RECEIVABLES | Наличие дебиторской задолженности по корпоративному клиенту |
| COMPANY_BAN | Наличие запрета со стороны Компании дистанционной торговли (интернет-магазина) на продление срока хранения |
| DELIVERY_POINT_CLOSED | ПВЗ закрыт |

---

### Тип операции из трекинга

| Значение | Описание |
|----------|----------|
| UNKNOWN | Тип операции не определен |
| ACCEPTING | Прием |
| GIVING | Вручение |
| RETURNING | Возврат |
| DELIVERING | Досылка почты |
| SKIPPING | Невручение |
| STORING | Хранение |
| HOLDING | Временное хранение |
| PROCESSING | Обработка |
| IMPORTING | Импорт международной почты |
| EXPORTING | Экспорт международной почты |
| CUSTOM_ACCEPTING | Принято таможней |
| TRYING | Неудачная попытка вручения |
| REGISTERING | Регистрация отправки |
| CUSTOM_LEGALIZING | Таможенное оформление |
| DELIGATING | Передача на временное хранение |
| DESTROYING | Уничтожение |
| ACCOUNTING | Передача вложения на баланс |
| LOSS_REGISTRATION | Регистрация утраты |
| CUSTOM_DUTY_RECEIVING | Таможенные платежи поступили |
| DM_REGISTRATION | Регистрация |
| DM_DELIVERING | Доставка |
| DM_NON_DELIVERING | Недоставка |
| TEMPORARY_STORING_ARRIVING | Поступление на временное хранение |
| PROLONGATION_CUSTOM_STORING | Продление срока выпуска таможней |
| OPENING | Вскрытие |
| CANCELLATION | Отмена |
| ID_ASSIGNMENT | Присвоен идентификатор |
| ELECTRONIC_REGISTRATION_RECEIVED | Получена электронная регистрация |
| REGISTRATION_PASSAGE_IN_MMPO | Регистрация прохождения в ММПО |
| SRM_DISPATCH | Отправка SRM |
| CARRIER_PROCESSING | Обработка перевозчиком |
| APO_RECEIPT | Поступление АПО |
| INTERNATIONAL_PROCESSING | Международная обработка |
| ELECTRONIC_NOTIFICATION_UPLOADED | Электронное уведомление загружено |
| REFUSED_COURIER_DELIVERY | Отказ в курьерской доставке |
| CLARIFICATION_DELIVERY_PAYMENT_TYPE | Уточнение вида оплаты доставки |
| PRE_FORMALIZATION | Предварительное оформление |
| RETAINED_FOR_CLARIFICATION_FROM_SENDER | Задержка для уточнений у отправителя |
| PRELIMINARY_CUSTOMS_DECLARATION | Предварительное таможенное декларирование |
| CUSTOMS_CONTROL | Таможенный контроль |
| CUSTOMS_CHARGES_PROCESSING | Обработка таможенных платежей |
| SECOND_UNSUCCESSFUL_DELIVERY_ATTEMPT | Вторая неудачная попытка вручения |
| DELIVERY_PERMITTED | Вручение разрешено |
| ACCEPTANCE_REJECTED | Отказ в приеме |
| ELECTRONIC_NOTIFICATION_REFUSED | Отказ от отправки электронного уведомления получателем |
| ID_ASSIGNMENT_CANCELATION | Отмена присвоения идентификатора |
| PARTIAL_DELIVERY | Частичное вручение |
| EXTEND_SHELF_LIFE_REFUSED | Отказ в продлении срока хранения |

---

### Категория РПО

| Значение | Описание |
|----------|----------|
| SIMPLE | Простое |
| ORDERED | Заказное |
| ORDINARY | Обыкновенное |
| WITH_DECLARED_VALUE | С объявленной ценностью |
| WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | С объявленной ценностью и наложенным платежом |
| WITH_DECLARED_VALUE_AND_COMPULSORY_PAYMENT | С объявленной ценностью и обязательным платежом |
| WITH_COMPULSORY_PAYMENT | С обязательным платежом |
| COMBINED_ORDINARY | Комбинированное обыкновенное |
| COMBINED_WITH_DECLARED_VALUE | Комбинированное с объявленной ценностью |
| COMBINED_WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | Комбинированное с объявленной ценностью и наложенным платежом |

---

### Разряд письма

| Значение | Описание |
|----------|----------|
| WO_RANK | Без разряда |
| GOVERNMENTAL | Правительственное |
| MILITARY | Воинское |
| OFFICIAL | Служебное |
| JUDICIAL | Судебное |
| PRESIDENTIAL | Президентское |
| CREDIT | Кредитное |
| ADMINISTRATIVE | Административное |

---

### Вид РПО

| Значение | Описание |
|----------|----------|
| POSTAL_PARCEL | Посылка "нестандартная" |
| ONLINE_PARCEL | Посылка "онлайн" |
| ONLINE_COURIER | Курьер "онлайн" |
| EMS | Отправление EMS |
| EMS_OPTIMAL | EMS оптимальное |
| EMS_RT | EMS РТ |
| EMS_TENDER | EMS тендер |
| LETTER | Письмо |
| LETTER_CLASS_1 | Письмо 1-го класса |
| BANDEROL | Бандероль |
| BUSINESS_COURIER | Бизнес курьер |
| BUSINESS_COURIER_ES | Бизнес курьер экпресс |
| PARCEL_CLASS_1 | Посылка 1-го класса |
| BANDEROL_CLASS_1 | Бандероль 1-го класса |
| VGPO_CLASS_1 | ВГПО 1-го класса |
| SMALL_PACKET | Мелкий пакет |
| EASY_RETURN | Легкий возврат |
| VSD | Отправление ВСД |
| ECOM | ЕКОМ |
| ECOM_MARKETPLACE | ЕКОМ Маркетплейс |
| HYPER_CARGO | Доставка день в день |
| COMBINED | Комбинированное |

---

### Категория уведомления о вручении РПО

| Значение | Описание |
|----------|----------|
| SIMPLE | Простое |
| ORDERED | Заказное |
| ELECTRONIC | Электронное |

---

### Способы оплаты

| Значение | Описание |
|----------|----------|
| CASH | наличными |
| CASHLESS | безналичными |
| FREE | бесплатно |
| PLASTIC_CARD | банковской картой |
| POSTAGE_STAMPS_SIGNS | государственные знаки почтовой оплаты марками |
| ADVANCE_PAYMENT | предоплата |
| PAID_INTERNATIONAL_OPERATOR | оплачено международному оператору |
| PAID_RECIPIENT | наложенным платежом |
| POSTAGE_STAMPS_FRANKING | государственные знаки почтовой оплаты - франкирование |

---

### Коды отметок внутренних и международных отправлений

| Значение | Описание |
|----------|----------|
| WITHOUT_MARK | Без отметки |
| WITH_SIMPLE_NOTICE | С простым уведомлением |
| WITH_ORDER_OF_NOTICE | С заказным уведомлением |
| WITH_INVENTORY | С описью |
| CAUTION_FRAGILE | Осторожно (Хрупкая/Терморежим) |
| HEAVY_HANDED | Тяжеловесная |
| LARGE_BULKY | Крупногабаритная (Громоздкая) |
| WITH_DELIVERY | С доставкой (Доставка нарочным) |
| AWARDED_IN_OWN_HANDS | Вручить в собственные руки |
| WITH_DOCUMENTS | С документами |
| WITH_GOODS | С товарами |
| NO_RETURN | Возврату не подлежит |
| NONSTANDARD | Нестандартная |
| BORDER | Приграничная |
| INSURED | С ОЦ |
| WITH_ELECTRONIC_NOTIFICATION | С электронным уведомлением |
| BUSINESS_COURIER_EXPRESS | Курьер бизнес-экспресс |
| NONSTANDARD_UPTO_10KG | Нестандартная до 10 кг |
| NONSTANDARD_UPTO_20KG | Нестандартная до 20 кг |
| WITH_CASH_ON_DELIVERY | С наложенным платежом |
| SAFETY_GUARANTEE | Гарантия сохранности |
| ASSURE_PACKAGE | Заверительный пакет |
| COURIER_DELIVERY | Доставка курьером |
| COMPLETENESS_CHECKING | Проверка комплектности |
| OVERSIZED | Негабаритная |
| RUPOST_PACKAGE | В упаковке Почты России |
| DELIVERY_WITH_COD | Оплата при получении |
| VSD | Возврат сопроводительных документов |
| EASY_RETURN | Легкий возврат |

---

### Тип печати (формат адресного ярлыка)

| Значение | Описание |
|----------|----------|
| PAPER | А5, 14.8 x 21 см, лазерная и струйная печать |
| THERMO | А6, 10 x 15 см, термопечать |

---

### Тип адреса возврата

| Значение | Описание |
|----------|----------|
| SENDER_ADDRESS | По другому адресу |
| POSTOFFICE_ADDRESS | В ОПС обслуживания |

---

### Режим транспортировки "transport-mode"

| Значение | Описание |
|----------|----------|
| STANDARD | Стандартный режим транспортировки |
| EXPRESS | Система ускоренной почты |
| SUPEREXPRESS | Суперэкспресс почта |

---

### Вид транспортировки

| Значение | Описание |
|----------|----------|
| SURFACE | Наземный |
| AVIA | Авиа |
| COMBINED | Комбинированный |
| EXPRESS | Системой ускоренной почты |
| STANDARD | Используется для отправлений "EMS Оптимальное" |

---

### Статус партии по гиперлокальной доставке

| Значение | Описание |
|----------|----------|
| BATCH_PROCESSING | Заявки в обработке |
| BATCH_EXECUTE | Заявки исполнены |
| BATCH_NOT_EXECUTE | Заявки не исполнены |
| BATCH_EXECUTE_PARTIALLY | Заявки исполнены частично |

---

### Тип заявления

| Значение | Описание |
|----------|----------|
| EARLY_RETURN | Досрочный возврат |

---

### Код качества нормализации адреса

| Значение | Описание |
|----------|----------|
| GOOD | Пригоден для почтовой рассылки |
| ON_DEMAND | До востребования |
| POSTAL_BOX | Абонентский ящик |
| UNDEF_01 | Не определен регион |
| UNDEF_02 | Не определен город или населенный пункт |
| UNDEF_03 | Не определена улица |
| UNDEF_04 | Не определен номер дома |
| UNDEF_05 | Не определена квартира/офис |
| UNDEF_06 | Не определен |
| UNDEF_07 | Иностранный адрес |

---

### Код проверки нормализации адреса

| Значение | Описание |
|----------|----------|
| CONFIRMED_MANUALLY | Подтверждено контролером |
| VALIDATED | Уверенное распознавание |
| OVERRIDDEN | Распознан: адрес был перезаписан в справочнике |
| NOT_VALIDATED_HAS_UNPARSED_PARTS | На проверку, неразобранные части |
| NOT_VALIDATED_HAS_ASSUMPTION | На проверку, предположение |
| NOT_VALIDATED_HAS_NO_MAIN_POINTS | На проверку, нет основных частей |
| NOT_VALIDATED_HAS_NUMBER_STREET_ASSUMPTION | На проверку, предположение по улице |
| NOT_VALIDATED_HAS_NO_KLADR_RECORD | На проверку, нет в КЛАДР |
| NOT_VALIDATED_HOUSE_WITHOUT_STREET_OR_NP | На проверку, нет улицы или населенного пункта |
| NOT_VALIDATED_HOUSE_EXTENSION_WITHOUT_HOUSE | На проверку, нет дома |
| NOT_VALIDATED_HAS_AMBI | На проверку, неоднозначность |
| NOT_VALIDATED_EXCEDED_HOUSE_NUMBER | На проверку, большой номер дома |
| NOT_VALIDATED_INCORRECT_HOUSE | На проверку, некорректный дом |
| NOT_VALIDATED_INCORRECT_HOUSE_EXTENSION | На проверку, некорректное расширение дома |
| NOT_VALIDATED_FOREIGN | Иностранный адрес |
| NOT_VALIDATED_DICTIONARY | На проверку, не по справочнику |

---

### Код качества нормализации телефона

| Значение | Описание |
|----------|----------|
| CONFIRMED_MANUALLY | Подтверждено контролером |
| GOOD | Корректный телефонный номер |
| GOOD_REPLACED_CODE | Изменен код телефонного номера |
| GOOD_REPLACED_NUMBER | Изменен номер телефона |
| GOOD_REPLACED_CODE_NUMBER | Изменен код и номер телефона |
| GOOD_CITY_CONFLICT | Конфликт по городу |
| GOOD_REGION_CONFLICT | Конфликт по региону |
| FOREIGN | Иностранный телефонный номер |
| CODE_AMBI | Неоднозначный код телефонного номера |
| EMPTY | Пустой телефонный номер |
| GARBAGE | Телефонный номер содержит некорректные символы |
| GOOD_CITY | Восстановлен город в телефонном номере |
| GOOD_EXTRA_PHONE | Запись содержит более одного телефона |
| UNDEF | Телефон не может быть распознан |
| INCORRECT_DATA | Телефон не может быть распознан |

---

### Код качества нормализации ФИО

| Значение | Описание |
|----------|----------|
| CONFIRMED_MANUALLY | Подтверждено контролером |
| EDITED | Правильное значение |
| NOT_SURE | Сомнительное значение |

---

### Статусы заявки на вызов курьера

| Значение | Описание |
|----------|----------|
| NOT_REQUIRED | Заявка на вызов курьера не требуется |
| AVAILABLE | Разрешена подача заявки на вызов курьера |
| REFUSED_BY_USER | Пользователь отказался от подачи заявки на вызок курьера |
| ORDER_IN_PROGRESS | Заявка на вызов курьера в процессе |
| ORDER_REJECTED | Заявка на вызов курьера отклонена на стороне КЦ |
| ATTEMPT_FAILED | Попытка отправки не удалась |
| ORDER_COMPLETED | Заявка завершена |
| MANUAL_DELIVERY | Самостоятельная доставка |

---

### Коды ответа метода оформления заявления на дополнительную услугу

| Код | Пример текста | Описание |
|-----|---------------|----------|
| 200 | 4657 | Успешный запрос, в ответ приходит id заявления |
| 400 | `{"code": "1005", "desc": "Invalid bank. It should not be empty."}` | Заявление не прошло валидацию |
| 401 | | Отправление оформлялось не от имени текущего пользователя |
| 403 | | Нарушение доступа |
| 404 | `{"code": "1001", "desc": "Отправление не найдено"}` | Указанный ШПИ отправления не найден |
| 500 | `{"timestamp": "2025-04-23T16:43:13", "status": "500", "error": "Internal Server Error", "path": "/1.0/claims/create"}` | Неправильный токен |
| 500 | `{"code": "1002", "desc": "SQL exception"}` | Подача заявления повторно |

---

### Результат электронного декларирования

| Значение | Описание |
|----------|----------|
| NEW | Новая |
| IN_PROGRESS | Направлено в ФТС. Для подписания перейдите по [ссылке](https://web2.edata.customs.ru/FtsPersonalCabinetWeb2017/#?view=List&service=MpoNds) |
| DONE | Разрешен выпуск товаров без уплаты таможенных платежей |
| REJECTED | Отказ в выпуске товаров |
| CANCELED | Декларирование отменено |
| FTS_ERROR | Отправить на декларирование не удалось. Повторите попытку позднее |
| TRANSIT | Отправлено на декларирование |
| ILLEGAL_DATA | Ошибка декларирования |

---

### Тип пункта выдачи

| Значение | Описание |
|----------|----------|
| DELIVERY_POINT | ПВЗ - пункт выдачи заказов |
| PICKUP_POINT | АПС - автоматизированная почтовая станция (почтамат) |

---

### Типоразмер

| Значение | Описание |
|----------|----------|
| S | до 260х170х80 мм |
| M | до 300х200х150 мм |
| L | до 400х270х180 мм |
| XL | 530х260х220 мм |
| OVERSIZED | Негабарит (сумма сторон не более 1200 мм, сторона не более 600 мм) |

---

### Статус необходимости скачивания новых документов

| Значение | Описание |
|----------|----------|
| F103 | Ф103 изменена |
| F103_AND_OPM | Ф103 и ярлыки со знаком онлайн-оплаты изменены |
| F103_AND_NEW_SHIPMENT | Ф103 изменена и есть новые отправления |
| TRANSPORT_BLANK | Изменена транспортная накладная |
| TRANSPORT_BLANK_AND_OPM | Изменена транспортная накладная и ярлыки со знаком онлайн-оплаты |
| TRANSPORT_BLANK_AND_NEW_SHIPMENT | Изменена транспортная накладная и есть новые отправления |

---

### Коды видов сервиса, используемого для отправлений

| Значение | Описание |
|----------|----------|
| WITHOUT_SERVICE | Без сервиса |
| WITHOUT_OPENING | Без вскрытия |
| CONTENTS_CHECKING | С проверкой вложения |
| WITH_FITTING | С примеркой |
| COURIER_DELIVERY | Доставка курьером |
| PARTIAL_REDEMPTION | С частичным выкупом |
| FUNCTIONALITY_CHECKING | С проверкой работоспособности |

---

### Ошибки

#### BatchError

**Метод:** POST /1.0/user/shipment, POST /1.0/batch/{name}/shipment

| Значение | Описание |
|----------|----------|
| ALL_SHIPMENTS_SENT | Все отправления уже отправлены |
| BARCODE_ERROR | Ошибка при получении ШПИ |
| EMPTY_ADDRESS_TYPE_TO | Тип адреса не указан |
| EMPTY_INDEX_TO | Почтовый индекс не указан |
| EMPTY_INSR_VALUE | Объявленная сумма не указана |
| EMPTY_MAIL_CATEGORY | Категория почтового отправления не указана |
| EMPTY_MAIL_DIRECT | Почтовое направление не указано |
| EMPTY_MAIL_TYPE | Тип почтового отправления не указан |
| EMPTY_MASS | Масса не указана |
| EMPTY_NUM_ADDRESS_TYPE | Не задан номер для соответствующего типа адреса |
| EMPTY_PAYMENT | Наложенный платеж не указан |
| EMPTY_PLACE_TO | Населенный пункт не указан |
| EMPTY_REGION_TO | Регион не заполнен |
| EMPTY_TRANSPORT_TYPE | Способ пересылки не указан |
| EMPTY_POSTOFFICE_CODE | Индекс приемного почтового отделения не задан |
| ILLEGAL_ADDRESS_TYPE_TO | Тип адреса некорректен |
| ILLEGAL_INDEX_TO | Почтовый индекс некорректен |
| ILLEGAL_INITIALS | ФИО некорректно |
| ILLEGAL_INSR_VALUE | Объявленная сумма некорректна |
| ILLEGAL_MAIL_CATEGORY | Категория почтового отправления некорректна |
| ILLEGAL_MAIL_DIRECT | Почтовое направление некорректно |
| ILLEGAL_MAIL_TYPE | Тип почтового отправления некорректен |
| ILLEGAL_MASS | Масса некорректна |
| ILLEGAL_MASS_EXCESS | Вес отправления не должен превышать N кг |
| ILLEGAL_PAYMENT | Наложенный платеж некорректен |
| ILLEGAL_POSTCODE | Индекс приемного почтового отделения в настройках и в партии отличаются |
| ILLEGAL_POSTOFFICE_CODE | Индекс приемного почтового отделения некорректен |
| ILLEGAL_TRANSPORT_TYPE | Некорректный способ пересылки |
| IMP13N_ERROR | Ошибка имперсонализации |
| INSR_VALUE_EXCEEDS_MAX | Превышено максимальное значение N руб |
| NO_AVAILABLE_POSTOFFICES | Нет доступных точек сдачи |
| NOT_FOUND | Отправление не найдено |
| PAST_DUE_DATE | Дата отправки просрочена |
| READONLY_STATE | Изменения в партии недопустимы |
| RESTRICTED_MAIL_CATEGORY | Для создания отправлений с наложенным платежом необходимо указать номер ЕСПП в настройках сервиса. Обратитесь к вашему персональному менеджеру в Почте или напишите письмо на почтовый ящик support.otpravka@russianpost.ru |
| SENDING_MAIL_FAILED | Ошибка при отправке почты |
| TARIFF_ERROR | Ошибка при расчете тарифа |
| DIFFERENT_TRANSPORT_TYPE | Способы пересылки отправления и партии отличаются |
| DIFFERENT_MAIL_TYPE | Типы почтовых отправлений не совпадают |
| DIFFERENT_MAIL_CATEGORY | Категории почтовых отправления не совпадают |
| DIFFERENT_MAIL_RANK | Разряд отправления и партии отличаются |
| ABSENT_OVERSIZE_POSTMARK | Отправление не может быть добавлено в партию с отметкой "Негабаритная" |
| UNEXPECTED_OVERSIZE_POSTMARK | Негабаритное отправление не может быть добавлено в партию без отметки "Негабаритная" |
| ABSENT_FRAGILE_POSTMARK | Отправление без отметки "Осторожно/Хрупкое/Терморежим" не может быть добавлено в партию с отметкой "Осторожно/Хрупкое/Терморежим" |
| UNEXPECTED_FRAGILE_POSTMARK | Отправление с отметкой "Осторожно/Хрупкое/Терморежим" не может быть добавлено в партию без отметки "Осторожно/Хрупкое/Терморежим" |
| ABSENT_COURIER_DELIVERY_POSTMARK | Отправление без отметки "Курьер" не может быть добавлено в партию с отметкой "Курьер" |
| UNEXPECTED_COURIER_DELIVERY_POSTMARK | Отправление с отметкой "Курьер" не может быть добавлено в партию без отметки "Курьер" |
| ABSENT_ORDER_OF_NOTICE_POSTMARK | Отправление без отметки "С заказным уведомлением" не может быть добавлено в партию с отметкой "С заказным уведомлением" |
| UNEXPECTED_ORDER_OF_NOTICE_POSTMARK | Отправление с отметкой "С заказным уведомлением" не может быть добавлено в партию без отметки "С заказным уведомлением" |
| ABSENT_SIMPLE_NOTICE_POSTMARK | Отправление без отметки "С простым уведомлением" не может быть добавлено в партию с отметкой "С простым уведомлением" |
| UNEXPECTED_SIMPLE_NOTICE_POSTMARK | Отправление с отметкой "С простым уведомлением" не может быть добавлено в партию без отметки "С простым уведомлением" |
| UNDEFINED | Неопределенная ошибка |

#### RemoveBacklogErrorCode

**Метод:** DELETE /1.0/backlog

| Значение | Описание |
|----------|----------|
| UNDEFINED | Неопределенная ошибка |
| ACCESS_VIOLATION | Нарушение доступа |
| NOT_FOUND | Не найден |

#### RemoveFromBatchErrorCode

**Метод:** POST /1.0/user/backlog, DELETE /1.0/shipment

| Значение | Описание |
|----------|----------|
| UNDEFINED | Неопределенная ошибка |
| DELIVERY_IN_PROGRESS | Отправление уже отправлено |
| ACCESS_VIOLATION | Нарушение доступа |
| NOT_FOUND | Не найден |
| READONLY_STATE | Изменения в партии недопустимы |

#### OrderValidationError

**Метод:** PUT /1.0/user/backlog, PUT /1.0/backlog/{id}, PUT /1.0/batch/{name}/shipment

| Значение | Описание |
|----------|----------|
| EMPTY_MAIL_CATEGORY | Категория почтового отправления не указана |
| ILLEGAL_MAIL_CATEGORY | Категория "%s" не поддерживается для данного типа отправления |
| RESTRICTED_MAIL_CATEGORY | Для создания отправлений с наложенным платежом необходимо указать номер ЕСПП в настройках сервиса. Обратитесь к вашему персональному менеджеру в Почте или напишите письмо на почтовый ящик support.otpravka@russianpost.ru |
| EMPTY_MAIL_TYPE | Тип почтового отправления не указан |
| ILLEGAL_MAIL_TYPE | Тип почтового отправления некорректен |
| EMPTY_ADDRESS_TYPE_TO | Тип адреса не указан |
| ILLEGAL_ADDRESS_TYPE_TO | Тип адреса некорректен |
| EMPTY_MAIL_DIRECT | Почтовое направление не указано |
| ILLEGAL_MAIL_DIRECT | Почтовое направление некорректно |
| ILLEGAL_INDEX_TO | Почтовый индекс некорректен |
| EMPTY_INDEX_TO | Почтовый индекс не указан |
| EMPTY_REGION_TO | Регион не заполнен |
| EMPTY_PLACE_TO | Населенный пункт не указан |
| EMPTY_TELADDRESS | Телефон получателя является обязательным для данного вида отправления |
| EMPTY_INSR_VALUE | Объявленная сумма не указана |
| ILLEGAL_INSR_VALUE | Объявленная сумма некорректна |
| INSR_VALUE_EXCEEDS_MAX | Превышено максимальное значение %s руб |
| EMPTY_PAYMENT | Наложенный платеж не указан |
| ILLEGAL_PAYMENT | Наложенный платеж некорректен |
| NOT_INSURED_PAYMENT | Наложенный платеж превышает объявленную ценность |
| EMPTY_TRANSPORT_TYPE | Способ пересылки не указан |
| ILLEGAL_TRANSPORT_TYPE | Сервис пока не поддерживает расчёт стоимости доставки в этот регион |
| EMPTY_MASS | Масса не указана |
| ILLEGAL_MASS | Масса некорректна |
| ILLEGAL_MASS_EXCESS | Превышение максимальной массы |
| TARIFF_ERROR | Ошибка тарификации (дополнительно поле см. Details) |
| IMP13N_ERROR | Ошибка имперсонализации |
| ILLEGAL_INITIALS | ФИО некорректно |
| EMPTY_NUM_ADDRESS_TYPE | Не задан номер для соответствующего типа адреса |
| BARCODE_ERROR | Ошибка при получении ШПИ |
| DIFFERENT_POSTCODE | Способы пересылки отправления и партии отличаются |
| EMPTY_POSTOFFICE_CODE | Индекс отделения места приема не задан |
| ILLEGAL_POSTOFFICE_CODE | Индекс приемного почтового отделения некорректен |
| NO_AVAILABLE_POSTOFFICES | Нет доступных отделений места приема |
| ILLEGAL_FRAGILE | Отметка "Осторожно/Хрупкое/Терморежим" неприменима для указанного типа отправлений |
| EMPTY_MAIL_RANK | Код разряда почтового отправления не задан в настройках пользователя |
| EMPTY_ENVELOPE_TYPE | Не задан тип конверта |
| ILLEGAL_ENVELOPE_TYPE | Недопустимое значение "Тип конверта" для выбранного вида отправления |
| ILLEGAL_ADDRESS_LETTER | Недопустимое значение "Литера" |
| ILLEGAL_ADDRESS_SLASH | Недопустимое значение "Дробь" |
| ILLEGAL_ADDRESS_CORPUS | Недопустимое значение "Корпус" |
| ILLEGAL_ADDRESS_BUILDING | Недопустимое значение "Строение" |
| ILLEGAL_ADDRESS_ROOM | Недопустимое значение "Комната" |
| EMPTY_PAYMENT_METHOD | Способ оплаты не задан |
| ILLEGAL_PAYMENT_METHOD | Некорректный способ оплаты |
| ABSENT_OVERSIZE_POSTMARK | Отправление не может быть добавлено в партию с отметкой "Негабаритная" |
| UNEXPECTED_OVERSIZE_POSTMARK | Негабаритное отправление не может быть добавлено в партию без отметки "Негабаритная" |
| ABSENT_COURIER_DELIVERY_POSTMARK | Отправление без отметки "Курьер" не может быть добавлено в партию с отметкой "Курьер" |
| UNEXPECTED_COURIER_DELIVERY_POSTMARK | Отправление с отметкой "Курьер" не может быть добавлено в партию без отметки "Курьер" |
| ABSENT_FRAGILE_POSTMARK | Отправление без отметки "Осторожно/Хрупкое/Терморежим" не может быть добавлено в партию с отметкой "Осторожно/Хрупкое/Терморежим" |
| UNEXPECTED_FRAGILE_POSTMARK | Отправление с отметкой "Осторожно/Хрупкое/Терморежим" не может быть добавлено в партию без отметки "Осторожно/Хрупкое/Терморежим" |
| ABSENT_ORDER_OF_NOTICE_POSTMARK | Отправление без отметки "С заказным уведомлением" не может быть добавлено в партию с отметкой "С заказным уведомлением" |
| UNEXPECTED_ORDER_OF_NOTICE_POSTMARK | Отправление с отметкой "С заказным уведомлением" не может быть добавлено в партию без отметки "С заказным уведомлением" |
| ABSENT_SIMPLE_NOTICE_POSTMARK | Отправление без отметки "С простым уведомлением" не может быть добавлено в партию с отметкой "С простым уведомлением" |
| UNEXPECTED_SIMPLE_NOTICE_POSTMARK | Отправление с отметкой "С простым уведомлением" не может быть добавлено в партию без отметки "С простым уведомлением" |
| UNDEFINED | Неопределенная ошибка |

#### TariffErrorCode

**Метод:** POST /1.0/tariff

| Значение | Описание |
|----------|----------|
| UNDEFINED | Ошибка при расчете тарифа |
| CODE_1372 | Доставка по указанному маршруту не осуществляется |

---

### Тип вложения

| Значение | Описание |
|----------|----------|
| GOODS | Товар |
| SERVICE | Услуга |

---

### Статус отправления по гиперлокальной доставке

| Значение | Описание |
|----------|----------|
| UNDEFINED | Неизвестный статус по заявке |
| CREATED | Заявка создана |
| DATA_VERIFIED | Заявка передана |
| DATA_VERIFICATION_FAILED | Ошибка при проверке заявки |
| CLIENT_VERIFIED | Клиент подтвержден |
| ROUTE_ASSIGNED | Назначен маршрут |
| COURIER_APPOINTED | Курьер назначен |
| CONTRACTOR_SELECTED | Курьер назначен |
| CONTRACTOR_SELECTION_FAILED | Не удалось подобрать курьера |
| PASSED_FOR_EXECUTION | Заявка передана в исполнение |
| ACCEPTED_FOR_EXECUTION_BY_CONTRACTOR | Заявка передана в исполнение |
| COURIER_ARRIVED_AT_PICKUP_PLACE | Курьер прибыл в место сбора |
| CARGO_PICKED_UP | Курьер забрал груз |
| COURIER_ARRIVED_AT_DELIVERY_PLACE | Курьер прибыл в место доставки |
| IN_FINAL_STAGES_OF_EXECUTION | Курьер прибыл в место доставки |
| CARGO_DELIVERED | Груз доставлен |
| COMPLETED | Заявка исполнена |
| CARGO_RETURN_INITIATED | Возврат заказа |
| CARGO_LOST_BY_CONTRACTOR | Исполнитель потерял отправление |
| CANCELLED_BY_CONTRACTOR | Заявка отменена курьером |
| CANCELLED_BY_CLIENT | Заявка отменена клиентом |
| CARGO_RETURNED | Груз возвращён на место возврата |
| PROCESSING_FAILED | Ошибка при исполнении заявки |

---

### Тип вложения

| Значение | Описание |
|----------|----------|
| WITHOUT_IDENTIFICATION | Без идентификации |
| PIN | Пин код (для почтоматов и партнерских ПВЗ) |
| IDENTITY_DOCUMENT | Документ удостоверяющий личность |
| ORDER_NUM_AND_FIO | Номер заказа и ФИО (для отделений почтовой связи) |

---

### Справочник признаков предмета расчета

| Значение | Описание |
|----------|----------|
| 1 | о реализуемом товаре, за исключением подакцизного товара (наименование и иные сведения, описывающие товар) |
| 2 | о реализуемом подакцизном товаре (наименование и иные сведения, описывающие товар) |
| 4 | об оказываемой услуге (наименование и иные сведения, описывающие услугу) |

---

### Код категории почтового отправления

| Значение | Описание |
|----------|----------|
| 0 | Простое |
| 1 | Заказное |
| 2 | С объявленной ценностью |
| 3 | Обыкновенное |
| 4 | С объявленной ценностью и наложенным платежом |
| 5 | Не определена |
| 6 | С объявленной ценностью и обязательным платежом |
| 7 | С обязательным платежом |
| 8 | Комбинированное обыкновенное |
| 9 | Комбинированное с объявленной ценностью |
| 10 | Комбинированное с объявленной ценностью и наложенным платежом |

---

### Код типа отправления

| Значение | Описание |
|----------|----------|
| 24 | Курьер Онлайн |

---

### Тип объекта в паспорте ОПС

*Данные загружаются динамически из API.*

---

### Признаки способов расчета

| Значение | Описание |
|----------|----------|
| 1 | Полная предварительная оплата до момента передачи предмета расчёта |
| 2 | Частичная предварительная оплата до момента передачи предмета расчёта |
| 3 | Аванс |
| 4 | Полная оплата, в том числе с учётом аванса (предварительной оплаты) в момент передачи предмета расчёта |
| 5 | Частичная оплата предмета расчёта в момент его передачи с последующей оплатой в кредит |
| 6 | Передача предмета расчёта без его оплаты в момент его передачи с последующей оплатой в кредит |
| 7 | Оплата предмета расчёта после его передачи с оплатой в кредит (оплата кредита) |

---

### Вид платежного средства

| Значение | Описание |
|----------|----------|
| 1 | Оплата банковской картой |
| 2 | Оплата электронной валютой |
| 3 | Оплата с помощью кредитной организации |
| 4 | Оплата дополнительным платежным средством |

---

### Способы оплаты

| Значение | Описание |
|----------|----------|
| CASHLESS | Безналичный расчет |
| STAMP | Оплата марками |
| FRANKING | Франкирование |
| TO_FRANKING | На франкировку |
| ONLINE_PAYMENT_MARK | Знак онлайн оплаты |

---

### Тип платежного средства

| Значение | Описание |
|----------|----------|
| 1 | Подарочные карты Мерчанта |
| 2 | Бонусы-авансы Мерчанта |
| 3 | Прямой аванс Мерчанта |
| 4 | Использование авансов/билетов |
| 5 | Платеж через кредитную организацию (банкомат) |
| 6 | Платеж через кредитную организацию (online) |
| 7 | Безналичное перечисление через банк |
| 8 | Оплата "онлайн кредитом" |
| 9 | Оплата по СМС |
| 10 | Эквайринг внешний |
| 11 | Платеж через терминал электронными |
| 12 | Платеж через терминал наличными |
| 13 | Наличные |
| 14 | Продажа в кредит |

---

### Продукты

| Значение | Описание |
|----------|----------|
| LETTER_ORDERED | Заказное письмо |
| LETTER_WITH_DECLARED_VALUE | Письмо с объявленной ценностью |
| LETTER_WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | Письмо с объявленной ценностью и наложенным платежом |
| INTERNATIONAL_LETTER_ORDERED | Международное заказное письмо |
| BANDEROL_SIMPLE | Простая бандероль (консолидатор) |
| BANDEROL_ORDERED | Заказная бандероль |
| BANDEROL_WITH_DECLARED_VALUE | Бандероль с объявленной ценностью |
| BANDEROL_WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | Бандероль с объявленной ценностью и наложенным платежом |
| POSTAL_PARCEL_ORDINARY | Посылка обыкновенная |
| POSTAL_PARCEL_WITH_DECLARED_VALUE | Посылка с объявленной ценностью |
| POSTAL_PARCEL_WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | Посылка с объявленной ценностью и наложенным платежом |
| INTERNATIONAL_POSTAL_PARCEL_ORDINARY | Посылка обыкновенная международная |
| EMS_ORDINARY | EMS обыкновенное |
| EMS_WITH_DECLARED_VALUE | EMS с объявленной ценностью |
| EMS_WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | EMS с объявленной ценностью и наложенным платежом |
| EMS_OPTIMAL_ORDINARY | EMS оптимальное обыкновенное |
| EMS_OPTIMAL_WITH_DECLARED_VALUE | EMS оптимальное с объявленной ценностью |
| EMS_OPTIMAL_WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | EMS оптимальное с объявленной ценностью и наложенным платежом |
| EMS_RT_ORDINARY | EMS РТ |
| EMS_RT_WITH_DECLARED_VALUE | EMS с объявленной ценностью |
| ONLINE_PARCEL_ORDINARY | Посылка онлайн обыкновенная |
| ONLINE_PARCEL_WITH_DECLARED_VALUE | Посылка онлайн с объявленной ценностью |
| ONLINE_PARCEL_WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | Посылка онлайн с объявленной ценностью и наложенным платежом |
| ONLINE_COURIER_ORDINARY | Курьер онлайн обыкновенное |
| ONLINE_COURIER_WITH_DECLARED_VALUE | Курьер онлайн с объявленной ценностью |
| ONLINE_COURIER_WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | Курьер онлайн с объявленной ценностью и наложенным платежом |
| BUSINESS_COURIER_ORDINARY | Бизнес Курьер обыкновненное |
| BUSINESS_COURIER_WITH_DECLARED_VALUE | Бизнес Курьер с объявленной ценностью |
| BUSINESS_COURIER_ES_ORDINARY | Бизнес Курьер экспресс обыкновненное |
| BUSINESS_COURIER_ES_WITH_DECLARED_VALUE | Бизнес Курьер экспресс с объявленной ценностью |
| PARCEL_CLASS_1_ORDINARY | Посылка 1-го класса обыкновенная |
| PARCEL_CLASS_1_WITH_DECLARED_VALUE | Посылка 1-го класса с объявленной ценностью |
| PARCEL_CLASS_1_WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | Посылка 1-го класса с объявленной ценностью и наложенным платежом |
| LETTER_CLASS_1_ORDERED | Письмо 1-го класса заказное |
| LETTER_CLASS_1_WITH_DECLARED_VALUE | Письмо 1-го класса с объявленной ценностью |
| LETTER_CLASS_1_WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | Письмо 1-го класса с объявленной ценностью и наложенным платежом |
| BANDEROL_CLASS_1_ORDERED | Бандероль 1 класса заказное |
| BANDEROL_CLASS_1_WITH_DECLARED_VALUE | Бандероль 1 класса с объявленной ценностью |
| BANDEROL_CLASS_1_WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY | Бандероль 1 класса с объявленной ценностью и наложенным платежом |
| LETTER_SIMPLE | Письмо обыкновенное (консолидатор) |
| SINGLE_LETTER_SIMPLE | Простое письмо единичное |
| SINGLE_BANDEROL_SIMPLE | Простая бандероль единичная |
| SMALL_PACKET_ORDERED | Мелкий пакет заказной |
| INTERNATIONAL_EMS_ORDINARY | EMS международное обыкновенное |
| INTERNATIONAL_SINGLE_LETTER_SIMPLE | Международное простое письмо |
| VGPO_CLASS_1_ORDERED | ВГПО 1-го класса заказное |
| VGPO_CLASS_1_SIMPLE | ВГПО 1-го класса простое |
| EMS_TENDER_ORDINARY | EMS Тендер |
| EMS_TENDER_WITH_DECLARED_VALUE | EMS Тендер с объявленной ценностью |
| VSD_ORDINARY | Отправление ВСД |
| ECOM_ORDINARY | ЕКОМ обыкновенное |
| ECOM_WITH_COMPULSORY_PAYMENT | ЕКОМ с обязательным платежом |
| ECOM_MARKETPLACE_WITH_DECLARED_VALUE | ЕКОМ Маркетплейс с объявленной ценностью |
| EASY_RETURN_ORDINARY | Легкий возврат обыкновенное |
| EASY_RETURN_WITH_DECLARED_VALUE | Легкий возврат с объявленной ценностью |

---

### Ошибки возвратов

#### CreateReturnError

**Метод:** PUT /1.0/returns, PUT /1.0/returns/return-without-direct

| Значение | Описание |
|----------|----------|
| DIRECT_SHIPMENT_NOT_FOUND | Прямое отправление не найдено |
| BARCODE_ERROR | Ошибка выдачи ШПИ |
| ONLINE_PAYMENT_MARK_ERROR | Ошибка ЗОО |
| SHIPMENT_API_ERROR | Ошибка при создании отправления в Shipment API |
| EASY_RETURN_NOT_SUPPORTED | Тип прямого отправления не поддерживает легкий возврат |
| EASY_RETURN_DISABLED | Легкий возрат не доступен для клиента |
| RETURN_ALREADY_EXIST | Возврат уже создан |
| ILLEGAL_DIRECT_SHIPMENT_STATE | Некорректный статус прямого отправления |
| FREE_ER_ADDRESS_NOT_ENABLED | Свободный ввод адреса не доступен |
| RETURN_SHIPMENT_NOT_FOUND | Возвратное отправление не найдено |
| ILLEGAL_RETURN_SHIPMENT_STATE | Возвратное отправление уже на маршруте |

#### DeleteReturnError

**Метод:** DELETE /1.0/returns/delete-separate-return

| Значение | Описание |
|----------|----------|
| RETURN_SHIPMENT_NOT_FOUND | Возвратное отправление не найдено |
| ILLEGAL_RETURN_SHIPMENT_STATE | Возвратное отправление уже на маршруте |

---

### Тип последней операции из трекинга

| Значение | Описание |
|----------|----------|
| UNKNOWN | Тип операции не определен |
| ACCEPTING | Прием |
| GIVING | Вручение |
| RETURNING | Возврат |
| DELIVERING | Досылка почты |
| SKIPPING | Невручение |
| STORING | Хранение |
| HOLDING | Временное хранение |
| PROCESSING | Обработка |
| IMPORTING | Импорт международной почты |
| EXPORTING | Экспорт международной почты |
| CUSTOM_ACCEPTING | Принято таможней |
| TRYING | Неудачная попытка вручения |
| REGISTERING | Регистрация отправки |
| CUSTOM_LEGALIZING | Таможенное оформление |
| DELIGATING | Передача на временное хранение |
| DESTROYING | Уничтожение |
| ACCOUNTING | Передача вложения на баланс |
| LOSS_REGISTRATION | Регистрация утраты |
| CUSTOM_DUTY_RECEIVING | Таможенные платежи поступили |
| DM_REGISTRATION | Регистрация |
| DM_DELIVERING | Доставка |
| DM_NON_DELIVERING | Недоставка |
| TEMPORARY_STORING_ARRIVING | Поступление на временное хранение |
| PROLONGATION_CUSTOM_STORING | Продление срока выпуска таможней |
| OPENING | Вскрытие |
| CANCELLATION | Отмена |
| ID_ASSIGNMENT | Присвоен идентификатор |

### Атрибут последней операции из трекинга

| Значение | Описание |
|----------|----------|
| UNKNOWN | Неизвестный атрибут |
| FOREIGN_ACCEPTING | Приём |
| SINGLE_ACCEPTING | Принято в отделении связи |
| PARTIAL_ACCEPTING | Принято в отделении связи |
| PARTIAL_ACCEPTING_REMOTE | Электронное письмо принято |
| GIVING_RECIPIENT | Получено адресатом |
| GIVING_SENDER | Получено отправителем |
| GIVING_RECIPIENT_IN_PO | Получено адресатом |
| GIVING_SENDER_IN_PO | Получено отправителем |
| GIVING_COMMON | Получено |
| GIVING_RECIPIENT_REMOTE | Электронное письмо вручено |
| GIVING_RECIPIENT_POSTMAN | Получено адресатом |
| GIVING_SENDER_POSTMAN | Получено отправителем |
| GIVING_RECIPIENT_COURIER | Получено адресатом |
| GIVING_RECIPIENT_CONTROL | Получено адресатом |
| GIVING_RECIPIENT_CONTROL_POSTMAN | Получено адресатом |
| GIVING_RECIPIENT_CONTROL_COURIER | Получено адресатом |
| GIVING_SENDER_COURIER | Получено отправителем |
| RETURNING_BY_EXPIRED_STORING | Отправлено обратно отправителю |
| RETURNING_BY_SENDER_REQUEST | Отправлено обратно отправителю |
| RETURNING_BY_RECEPIENT_ABSENCE | Отправлено обратно отправителю |
| RETURNING_BY_RECEPIENT_REJECT | Отправлено обратно отправителю |
| RETURNING_BY_RECEPIENT_DEATH | Отправлено обратно отправителю |
| RETURNING_BY_UNREADABLE_ADDRESS | Отправлено обратно отправителю |
| RETURNING_BY_CUSTOM | Отправлено обратно отправителю |
| RETURNING_BY_UNKNOWN_RECEPIENT | Отправлено обратно отправителю |
| RETURNING_BY_OTHER_REASONS | Отправлено обратно отправителю |
| RETURNING_BY_WRONG_ADRESS | Отправлено обратно отправителю |
| DELIVERING_BY_CLIENT_REQUEST | Перенаправлено на другой адрес |
| DELIVERING_TO_NEW_ADDRESS | Перенаправлено на новый адрес |
| DELIVERING_BY_ROUTER | Перенаправлено на новый адрес |
| LOST | Вручение не состоялось |
| CONFISCATED | Вручение не состоялось |
| SKIPPING_BY_ERROR | Вручение не состоялось |
| SKIPPING_BY_CUSTOM | Вручение не состоялось |
| UNDELIVERED | Вручение не состоялось |
| POSTE_RESTANTE_STORING | Хранение |
| STORING_IN_BOX | Хранение |
| TEMPORAL_STORING | Хранение |
| ADDITIONAL_STORING | Хранение |
| CUSTOM_HOLDING | Передано в таможенный орган |
| CUSTOM_DUTY_RECEIVED | Таможенные платежи поступили |
| UNASSIGNED | Временное хранение |
| UNCLAIMED | Временное хранение |
| PROHIBITED | Временное хранение |
| SORTING | Сортировка |
| SENT | Покинуло место приема |
| ARRIVED | Прибыло в место вручения |
| DELIVERED_TO_SORTING | Прибыло в сортировочный центр |
| SORTED | Покинуло сортировочный центр |
| DELIVERED_TO_EXCHANGE_HUB | Прибыло в место международного обмена |
| PROCESSED_BY_EXCHANGE_HUB | Покинуло место международного обмена |
| DELIVERED_TO_HUB | Прибыло в место транзита |
| LEAVED_HUB | Покинуло место транзита |
| DELIVERED_TO_PO | Ожидает адресата в почтомате |
| DELIVERED_HYBRID | Прибыло в центр гибридной печати |
| EXPIRED_PO_STORING | Истекает срок хранения в почтомате |
| FORWARDED | Переадресовано в почтомат |
| GET | Изъято из почтомата |
| ARRIVED_IN_RUSSIA | Прибыло на территорию России |
| ARRIVED_IN_PARCELS_CENTER | Ожидает адресата в месте вручения |
| GIVEN_TO_COURIER | Передано курьеру |
| GIVEN_FOR_REMOTE | Электронное письмо доставлено |
| GIVEN_FOR_BOXROOM | Передано в кладовую хранения |
| GIVEN_TO_POSTMAN | Передано почтальону |
| COURIER_ORDERED | Передано курьеру |
| IMPORTED | Прошло регистрацию |
| EXPORTED | Пересекло границу |
| ACCEPTED_BY_CUSTOM | Принято таможней |
| FAILED_BY_TEMPORAL_ABSENCE_OF_RECEPIENT | Неудачная попытка вручения |
| FAILED_BY_DELAYING_REQUEST | Неудачная попытка вручения |
| FAILED_BY_UNFILLED_ADDRESS | Неудачная попытка вручения |
| FAILED_BY_INVALID_ADDRESS | Неудачная попытка вручения |
| FAILED_BY_RECEPIENT_LEAVING | Неудачная попытка вручения |
| FAILED_BY_RECEPINT_REJECT | Неудачная попытка вручения |
| UNOVERCAMING_FAIL | Неудачная попытка вручения |
| FAILED_WITH_ANOTHER_REASON | Неудачная попытка вручения |
| WAITING_RECEPIENT_IN_OFFICE | Неудачная попытка вручения |
| RECEPIENT_NOT_FOUND | Неудачная попытка вручения |
| TECHNICALLY_FAILED | Неудачная попытка вручения |
| FAILED_BY_EXPIRATION_TIME | Неудачная попытка вручения |
| REGISTERED | Регистрация отправки |
| LEGALIZED | Выпущено таможней |
| CUSTOM_LEGALIZED | Выпущено таможней |
| CANCELED_LEGLIZATION | Возвращено таможней |
| PROCESSED_BY_CUSTOM | Осмотрено таможней |
| REJECTED_BY_CUSTOM | Отказано таможней в выпуске |
| PASSED_WITH_CUSTOM_NOTIFY | Направлено с таможенным уведомлением |
| PASSED_WITH_CUSTOM_TAX | Направлено с обязательной уплатой таможенных платежей |
| DELIGATED | Передано на временное хранение |
| DESTROYED | Уничтожение |
| ACCOUNTED | Передано в собственность почты |
| LOSS_REGISTERED | Зарегистрирована утрата |
| DM_REGISTERED | Регистрация |
| DM_DELIVERED | Доставка |
| DM_ABSENCE_POSTBOX | Недоставка |
| Т | Недоставка |
| DM_WRONG_POSTOFFICE_INDEX | Недоставка |
| DM_WRONG_ADDRESS | Недоставка |
| OPENED | Срок хранения истек, отправление вскрыто |
| CANCELED_BY_SENDER_DEFAULT | Предыдущая операция отменена по требованию отправителя |
| CANCELED_BY_SENDER | Предыдущая операция отменена по требованию отправителя |
| CANCELED_BY_OPERATOR | Предыдущая операция отменена |
| ID_ASSIGNED | Зарегистрировано, еще не отправлено |

---

### Справочник ставок НДС

| Значение | Описание |
|----------|----------|
| -1 | не облагается НДС |
| 0 | облагается НДС по ставке 0% |
| 10 | облагается НДС по ставке 10% |
| 18 | облагается НДС по ставке 18% (с 01.01.2019 -- по ставке 20%) |
| 110 | облагается НДС по ставке 10/110 |
| 118 | облагается НДС по ставке 18/118 (с 01.01.2019 -- по ставке 20/120) |
