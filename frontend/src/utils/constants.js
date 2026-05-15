export const LISTING_STATUS_COLORS = {
  active: 'bg-emerald-100 text-emerald-700',
  discounted: 'bg-amber-100 text-amber-700',
  free: 'bg-sky-100 text-sky-700',
  draft: 'bg-gray-100 text-gray-600',
  paused: 'bg-gray-100 text-gray-600',
  sold_out: 'bg-red-100 text-red-700',
  compost: 'bg-stone-100 text-stone-700',
}

export const LISTING_STATUS_LABELS = {
  active: 'В продаже',
  discounted: 'Скидка',
  free: 'Бесплатно',
  draft: 'Черновик',
  paused: 'Пауза',
  sold_out: 'Распродано',
  compost: 'Списано',
}

export const ORDER_STATUS_COLORS = {
  pending: 'bg-amber-100 text-amber-700',
  confirmed: 'bg-emerald-100 text-emerald-700',
  ready_for_pickup: 'bg-sky-100 text-sky-700',
  picked_up: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-700',
  expired: 'bg-stone-100 text-stone-700',
}

export const ORDER_STATUS_LABELS = {
  pending: 'Ожидает',
  confirmed: 'Подтвержден',
  ready_for_pickup: 'Готов',
  picked_up: 'Получен',
  cancelled: 'Отменен',
  expired: 'Истек',
}

export const ALLERGEN_LABELS = {
  none: 'Нет аллергенов',
  gluten: 'Глютен',
  dairy: 'Молоко',
  eggs: 'Яйца',
  nuts: 'Орехи',
  soy: 'Соя',
  fish: 'Рыба',
  shellfish: 'Морепродукты',
  sesame: 'Кунжут',
}
