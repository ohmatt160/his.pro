import { useEffect, useMemo, useRef, useState } from "react";
import { Download, FileText, Image, MessageSquare, Paperclip, RefreshCw, Search, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/context/AuthContext";
import { apiClient } from "@/api/client";
import {
  staffChatApi,
  type ChatConversation,
  type ChatMessage,
  type ChatStaff,
} from "@/api/staffChat";

const roleLabel = (role: string) =>
  role
    .toLowerCase()
    .replace("lab_tech", "lab staff")
    .replace("receptionist", "reception")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

const dateLabel = (value: string) => {
  const date = new Date(value);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  return date.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
};

const apiFileUrl = (path?: string | null) => {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  const base = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "") || "/api/v1";
  return `${base}/${path.replace(/^\/+/, "")}`;
};

const Chat = () => {
  const { user } = useAuth();
  const [staff, setStaff] = useState<ChatStaff[]>([]);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<ChatConversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const refresh = async () => {
    setError("");
    try {
      const [staffList, conversationList] = await Promise.all([
        staffChatApi.getStaff(),
        staffChatApi.getConversations(),
      ]);
      setStaff(staffList);
      setConversations(conversationList);
      if (activeConversation) {
        const refreshed = conversationList.find((conversation) => conversation.id === activeConversation.id);
        if (refreshed) setActiveConversation(refreshed);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load chat.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const staffTimer = window.setInterval(refresh, 30000);
    return () => window.clearInterval(staffTimer);
  }, []);

  useEffect(() => {
    if (!activeConversation) {
      setMessages([]);
      return;
    }

    let cancelled = false;
    staffChatApi
      .getMessages(activeConversation.id, { limit: 100 })
      .then((nextMessages) => {
        if (!cancelled) {
          setMessages(nextMessages);
          staffChatApi.markRead(activeConversation.id).then(refresh).catch(() => undefined);
        }
      })
      .catch((messageError) => {
        if (!cancelled) {
          setError(messageError instanceof Error ? messageError.message : "Could not load messages.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activeConversation?.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, activeConversation?.id]);

  const filteredStaff = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return staff;
    return staff.filter((member) =>
      [member.full_name, member.username, roleLabel(member.role), member.department || ""]
        .join(" ")
        .toLowerCase()
        .includes(normalized)
    );
  }, [query, staff]);

  const conversationByStaff = useMemo(() => {
    return new Map(conversations.map((conversation) => [conversation.other_staff.id, conversation]));
  }, [conversations]);

  const openStaff = async (member: ChatStaff) => {
    setError("");
    try {
      const conversation = conversationByStaff.get(member.id) || (await staffChatApi.createConversation(member.id));
      setActiveConversation(conversation);
      setConversations((current) => {
        const withoutDuplicate = current.filter((item) => item.id !== conversation.id);
        return [conversation, ...withoutDuplicate];
      });
    } catch (openError) {
      setError(openError instanceof Error ? openError.message : "Could not open conversation.");
    }
  };

  const send = async () => {
    const content = draft.trim();
    if (!activeConversation || !content || isSending) return;
    setIsSending(true);
    setError("");
    try {
      const message = await staffChatApi.sendMessage(activeConversation.id, {
        content,
        message_type: "text",
      });
      setMessages((current) => [...current, message]);
      setDraft("");
      await refresh();
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "Message could not be sent.");
    } finally {
      setIsSending(false);
    }
  };

  const attachFile = async (file: File) => {
    if (!activeConversation) return;
    setIsSending(true);
    setError("");
    try {
      const upload = await staffChatApi.uploadFile(file);
      const message = await staffChatApi.sendMessage(activeConversation.id, {
        message_type: upload.file_type.startsWith("image/") ? "image" : "file",
        file_name: upload.file_name,
        file_url: upload.file_url,
        file_size: upload.file_size,
        file_type: upload.file_type,
      });
      setMessages((current) => [...current, message]);
      await refresh();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Attachment could not be sent.");
    } finally {
      setIsSending(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const downloadAttachment = async (message: ChatMessage) => {
    if (!message.file_url) return;
    const blob = await apiClient.downloadBlob(message.file_url);
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = message.file_name || "attachment";
    link.click();
    URL.revokeObjectURL(objectUrl);
  };

  return (
    <main className="min-h-screen bg-background p-4 sm:p-6">
      <div className="mx-auto flex max-w-7xl flex-col gap-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{user?.facilitySlug}</p>
            <h1 className="text-2xl font-extrabold tracking-tight">Staff Messages</h1>
          </div>
          <Button variant="outline" className="gap-2" onClick={refresh}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
        </div>

        {error && (
          <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <Card className="overflow-hidden border-border/60">
          <CardContent className="grid min-h-[72vh] p-0 lg:grid-cols-[320px_1fr]">
            <aside className="border-b border-border bg-card lg:border-b-0 lg:border-r">
              <div className="border-b border-border p-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search staff..."
                    className="pl-9"
                  />
                </div>
              </div>
              <div className="max-h-[64vh] overflow-y-auto p-2">
                {isLoading ? (
                  <div className="space-y-2 p-2">
                    {Array.from({ length: 5 }).map((_, index) => (
                      <div key={index} className="h-14 animate-pulse rounded-lg bg-muted" />
                    ))}
                  </div>
                ) : filteredStaff.length === 0 ? (
                  <div className="p-8 text-center text-sm text-muted-foreground">No staff found.</div>
                ) : (
                  filteredStaff.map((member) => {
                    const conversation = conversationByStaff.get(member.id);
                    const active = activeConversation?.other_staff.id === member.id;
                    return (
                      <button
                        key={member.id}
                        type="button"
                        onClick={() => openStaff(member)}
                        className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left transition-colors ${
                          active ? "bg-primary/10" : "hover:bg-muted"
                        }`}
                      >
                        <span className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
                          {member.full_name.slice(0, 2).toUpperCase()}
                          <span
                            className={`absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-card ${
                              member.is_online ? "bg-emerald-500" : "bg-muted-foreground"
                            }`}
                          />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-semibold">{member.full_name}</span>
                          <span className="block truncate text-xs text-muted-foreground">{roleLabel(member.role)}</span>
                        </span>
                        {Boolean(conversation?.unread_count) && (
                          <Badge className="rounded-full">{conversation?.unread_count}</Badge>
                        )}
                      </button>
                    );
                  })
                )}
              </div>
            </aside>

            <section className="flex min-h-[72vh] flex-col">
              {!activeConversation ? (
                <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
                  <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                    <MessageSquare className="h-7 w-7" />
                  </div>
                  <h2 className="text-lg font-bold">Select a staff member</h2>
                  <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                    Choose someone from your facility staff list to start a secure conversation.
                  </p>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between border-b border-border p-4">
                    <div>
                      <h2 className="font-bold">{activeConversation.other_staff.full_name}</h2>
                      <p className="text-xs text-muted-foreground">
                        {roleLabel(activeConversation.other_staff.role)} ·{" "}
                        {activeConversation.other_staff.is_online ? "Online" : "Offline"}
                      </p>
                    </div>
                  </div>

                  <div className="flex-1 space-y-4 overflow-y-auto bg-muted/20 p-4">
                    {messages.map((message, index) => {
                      const mine = message.sender_id === user?.id;
                      const previous = messages[index - 1];
                      const showDate = !previous || dateLabel(previous.created_at) !== dateLabel(message.created_at);
                      return (
                        <div key={message.id}>
                          {showDate && (
                            <div className="my-4 text-center text-xs font-medium text-muted-foreground">
                              {dateLabel(message.created_at)}
                            </div>
                          )}
                          <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                            <div
                              className={`max-w-[78%] rounded-2xl px-4 py-2 text-sm shadow-sm ${
                                mine
                                  ? "rounded-br-md bg-primary text-primary-foreground"
                                  : "rounded-bl-md bg-card text-foreground"
                              }`}
                            >
                              {message.content && <p className="whitespace-pre-wrap">{message.content}</p>}
                              {message.file_url && (
                                <div className="mt-1 space-y-2">
                                  {message.message_type === "image" ? (
                                    <img
                                      src={apiFileUrl(message.file_url)}
                                      alt={message.file_name || "attachment"}
                                      className="max-h-56 rounded-lg object-cover"
                                    />
                                  ) : (
                                    <div className="flex items-center gap-2">
                                      <FileText className="h-4 w-4" />
                                      <span className="truncate">{message.file_name}</span>
                                    </div>
                                  )}
                                  <Button
                                    type="button"
                                    variant={mine ? "secondary" : "outline"}
                                    size="sm"
                                    className="h-8 gap-2"
                                    onClick={() => downloadAttachment(message)}
                                  >
                                    <Download className="h-3.5 w-3.5" /> Download
                                  </Button>
                                </div>
                              )}
                              <p className={`mt-1 text-[10px] ${mine ? "text-primary-foreground/70" : "text-muted-foreground"}`}>
                                {new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                              </p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                    <div ref={bottomRef} />
                  </div>

                  <div className="border-t border-border p-4">
                    <div className="flex items-end gap-2">
                      <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx"
                        onChange={(event) => {
                          const file = event.target.files?.[0];
                          if (file) attachFile(file);
                        }}
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isSending}
                      >
                        <Paperclip className="h-4 w-4" />
                      </Button>
                      <Input
                        value={draft}
                        onChange={(event) => setDraft(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" && !event.shiftKey) {
                            event.preventDefault();
                            send();
                          }
                        }}
                        placeholder="Type a secure message..."
                        disabled={isSending}
                      />
                      <Button type="button" className="gap-2" onClick={send} disabled={isSending || !draft.trim()}>
                        <Send className="h-4 w-4" /> Send
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </section>
          </CardContent>
        </Card>
      </div>
    </main>
  );
};

export default Chat;
