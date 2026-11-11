import { useMutation } from '@tanstack/react-query';
import { api } from '@/shared/api';

export const useAskAssistant = () =>
  useMutation({ mutationFn: (question: string) => api.assistant.ask(question) });
