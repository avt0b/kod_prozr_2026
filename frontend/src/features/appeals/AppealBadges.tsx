import { Badge } from '@mantine/core';
import type { AppealCategory, AppealStatus } from '@/shared/api';
import {
  APPEAL_CATEGORY_LABELS,
  APPEAL_STATUS_COLORS,
  APPEAL_STATUS_LABELS,
} from '@/shared/lib/labels';

export const AppealStatusBadge = ({ status }: { status: AppealStatus }) => (
  <Badge color={APPEAL_STATUS_COLORS[status]} variant="light">
    {APPEAL_STATUS_LABELS[status]}
  </Badge>
);

export const AppealCategoryBadge = ({ category }: { category?: AppealCategory | null }) =>
  category ? (
    <Badge color={category === 'other' ? 'gray' : 'red'} variant="outline">
      {APPEAL_CATEGORY_LABELS[category]}
    </Badge>
  ) : (
    <Badge color="gray" variant="outline">
      не определена
    </Badge>
  );
