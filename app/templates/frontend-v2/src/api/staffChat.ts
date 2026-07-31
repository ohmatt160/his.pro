import { apiClient } from "@/api/client";

export type ChatStaff = {
  id: string;
  username: string;
  full_name: string;
  role: string;
  department?: string | null;
  is_online: boolean;
  last_active?: string | null;
};

export type ChatSender = {
  id: string;
  username: string;
  full_name: string;
  role: string;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  facility_slug: string;
  sender_id: string;
  sender: ChatSender;
  content?: string | null;
  message_type: "text" | "file" | "image";
  file_name?: string | null;
  file_url?: string | null;
  file_size?: number | null;
  file_type?: string | null;
  is_read: boolean;
  read_at?: string | null;
  created_at: string;
};

export type ChatConversation = {
  id: string;
  facility_slug: string;
  participant_ids: string[];
  other_staff: ChatStaff;
  last_message?: ChatMessage | null;
  unread_count: number;
  last_message_at?: string | null;
  created_at: string;
};

export type ChatUpload = {
  file_url: string;
  file_name: string;
  file_size: number;
  file_type: string;
};

export const staffChatApi = {
  getStaff: () => apiClient.get<ChatStaff[]>("/chat/staff"),
  getConversations: () => apiClient.get<ChatConversation[]>("/chat/conversations"),
  createConversation: (participantId: string) =>
    apiClient.post<ChatConversation>("/chat/conversations", { participant_id: participantId }),
  getMessages: (conversationId: string, params?: { limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return apiClient.get<ChatMessage[]>(`/chat/conversations/${conversationId}/messages${suffix}`);
  },
  sendMessage: (
    conversationId: string,
    data: {
      content?: string;
      message_type: "text" | "file" | "image";
      file_name?: string;
      file_url?: string;
      file_size?: number;
      file_type?: string;
    }
  ) => apiClient.post<ChatMessage>(`/chat/conversations/${conversationId}/messages`, data),
  uploadFile: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.post<ChatUpload>("/chat/upload", formData);
  },
  markRead: (conversationId: string) =>
    apiClient.put<{ unread_count: number }>(`/chat/conversations/${conversationId}/read`),
  getUnreadCount: () => apiClient.get<{ unread_count: number }>("/chat/unread-count"),
};
