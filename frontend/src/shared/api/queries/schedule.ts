import { useQuery } from '@tanstack/react-query';
import { scheduleApi } from '../scheduleApi';

export const scheduleKeys = {
  all: ['schedule'] as const,
  range: (startDate: string, endDate: string) =>
    [...scheduleKeys.all, startDate, endDate] as const,
};

export function useSchedule(startDate: string, endDate: string) {
  return useQuery({
    queryKey: scheduleKeys.range(startDate, endDate),
    queryFn: () => scheduleApi.getSchedule({ start_date: startDate, end_date: endDate }),
    staleTime: 5 * 60_000,
  });
}
