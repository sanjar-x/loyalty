export const productCategoryTree = [
  {
    id: 'fashion',
    label: 'Одежда, обувь и аксессуары',
    children: [
      {
        id: 'clothes',
        label: 'Одежда',
        children: [
          { id: 'tshirts', label: 'Футболки' },
          { id: 'hoodies', label: 'Худи' },
          { id: 'zip-hoodies', label: 'Зип-худи' },
          { id: 'jeans', label: 'Джинсы' },
          { id: 'pants', label: 'Штаны' },
          { id: 'shorts', label: 'Шорты' },
          { id: 'tanks', label: 'Майки' },
          { id: 'longsleeves', label: 'Лонгсливы' },
          { id: 'sweatshirts', label: 'Свитшоты' },
          { id: 'sweaters', label: 'Свитеры' },
          { id: 'shirts', label: 'Рубашки' },
          { id: 'windbreakers', label: 'Ветровки' },
          { id: 'bombers', label: 'Бомберы' },
          { id: 'jackets', label: 'Куртки' },
          { id: 'puffers', label: 'Пуховики' },
          { id: 'vests', label: 'Жилеты' },
          { id: 'socks', label: 'Носки' },
          { id: 'underwear', label: 'Нижнее бельё' },
        ],
      },
      {
        id: 'shoes',
        label: 'Обувь',
        children: [
          { id: 'sneakers', label: 'Кроссовки' },
          { id: 'trainers', label: 'Кеды' },
          { id: 'shoes-classic', label: 'Туфли' },
          { id: 'flip-flops', label: 'Шлепанцы' },
          { id: 'boots', label: 'Ботинки' },
        ],
      },
      {
        id: 'accessories',
        label: 'Аксессуары',
        children: [
          { id: 'bags', label: 'Сумки' },
          { id: 'watches', label: 'Часы' },
          { id: 'jewelry', label: 'Украшения' },
          { id: 'backpacks', label: 'Рюкзаки' },
          { id: 'belts', label: 'Ремни' },
          { id: 'caps', label: 'Кепки' },
          { id: 'beanies', label: 'Шапки' },
          { id: 'glasses', label: 'Очки' },
          { id: 'wallets', label: 'Кошельки' },
        ],
      },
    ],
  },
];

export function findProductCategoryPath(rootId, groupId, leafId) {
  const root = productCategoryTree.find((item) => item.id === rootId) ?? null;
  const group = root?.children?.find((item) => item.id === groupId) ?? null;
  const leaf = group?.children?.find((item) => item.id === leafId) ?? null;

  return { root, group, leaf };
}
