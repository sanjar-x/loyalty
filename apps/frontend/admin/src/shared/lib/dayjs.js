import dayjs from 'dayjs';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import localizedFormat from 'dayjs/plugin/localizedFormat';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/ru';

dayjs.extend(isSameOrAfter);
dayjs.extend(isSameOrBefore);
dayjs.extend(localizedFormat);
// relativeTime backs `.fromNow()` / `.toNow()` (e.g. "через 2 дня"); used by
// invitation expiry chips and any future "X minutes ago" display.
dayjs.extend(relativeTime);
dayjs.locale('ru');

export default dayjs;
