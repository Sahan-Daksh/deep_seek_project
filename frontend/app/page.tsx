"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { Mic, MicOff, Pause, Play, Send, Upload, X, AlertCircle, MessageSquare, Plus, Square } from "lucide-react";
import { formatDistance } from "date-fns";
import WebSocketClient from "./WebSocketClient";

interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
  attachments?: Array<{
    name: string;
    url: string;
    type: string;
  }>;
}

interface Chat {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: Date;
  messages: Message[];
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [micError, setMicError] = useState<string | null>(null);
  const [recentChats, setRecentChats] = useState<Chat[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  const handleWebSocketMessage = (message: string) => {
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      content: message,
      role: "assistant",
      timestamp: new Date()
    }]);
  };

  const handleWebSocketError = (error: string) => {
    console.error("WebSocket error:", error);
    setMicError(error);
  };

  const handleWebSocketConnect = () => {
    console.log("WebSocket connected");
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setAttachments(prev => [...prev, ...Array.from(e.target.files!)]);
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!input.trim() && attachments.length === 0) return;

    const newMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: "user",
      timestamp: new Date(),
      attachments: attachments.map(file => ({
        name: file.name,
        url: URL.createObjectURL(file),
        type: file.type
      }))
    };

    setMessages(prev => [...prev, newMessage]);
    setInput("");

    if (attachments.length > 0) {
      const formData = new FormData();
      attachments.forEach(file => {
        formData.append("file", file);
      });
      formData.append("prompt", input);

      try {
        const response = await fetch("http://localhost:8000/upload", {
          method: "POST",
          body: formData,
        });
        const data = await response.json();
        handleWebSocketMessage(data.response);
      } catch (error) {
        console.error("Upload error:", error);
        handleWebSocketError("Failed to upload file");
      }
      setAttachments([]);
    } else {
      socketRef.current?.send(JSON.stringify({
        prompt: input
      }));
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Add recording logic here
      setIsRecording(true);
      setMicError(null);
    } catch (error) {
      console.error("Error accessing microphone:", error);
      setMicError("Could not access microphone");
    }
  };

  const togglePause = () => {
    setIsPaused(!isPaused);
  };

  const stopRecording = () => {
    setIsRecording(false);
    setIsPaused(false);
    setRecordingTime(0);
  };

  const endCurrentChat = () => {
    setMessages([]);
    setCurrentChatId(null);
  };

  return (
    <div className="flex h-screen">
      <WebSocketClient 
        onMessage={handleWebSocketMessage}
        onError={handleWebSocketError}
        onConnect={handleWebSocketConnect}
      />
      
      {/* Sidebar */}
      <div className="w-64 bg-card border-r border-border p-4">
        <Button 
          className="w-full mb-4 gap-2" 
          onClick={() => endCurrentChat()}
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
        
        <ScrollArea className="h-[calc(100vh-6rem)]">
          <div className="space-y-2">
            {recentChats.map(chat => (
              <Button
                key={chat.id}
                variant="ghost"
                className="w-full justify-start gap-2"
                onClick={() => setCurrentChatId(chat.id)}
              >
                <MessageSquare className="h-4 w-4" />
                {chat.title}
              </Button>
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Title and Controls */}
        <div className="p-4 border-b border-border bg-card flex justify-between items-center">
          <h1 className="text-2xl font-bold">Deepseek Chatbot</h1>
          <Button
            variant="outline"
            onClick={endCurrentChat}
            className="gap-2"
          >
            <Square className="h-4 w-4" />
            End Chat
          </Button>
        </div>

        <div className="flex-1 p-4 flex flex-col">
          <Card className="flex-grow mb-4 p-4">
            <ScrollArea className="h-[calc(100vh-280px)]">
              <div className="space-y-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.role === "assistant" ? "justify-start" : "justify-end"
                    }`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg p-4 ${
                        message.role === "assistant"
                          ? "bg-secondary"
                          : "bg-primary text-primary-foreground"
                      }`}
                    >
                      <p>{message.content}</p>
                      {message.attachments && (
                        <div className="mt-2 space-y-1">
                          {message.attachments.map((attachment) => (
                            <div
                              key={attachment.name}
                              className="text-sm opacity-90"
                            >
                              📎 {attachment.name}
                            </div>
                          ))}
                        </div>
                      )}
                      <p className="text-xs mt-2 opacity-70">
                        {formatDistance(message.timestamp, new Date(), {
                          addSuffix: true,
                        })}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </Card>

          <form onSubmit={handleSubmit} className="space-y-4">
            {micError && (
              <div className="flex items-center gap-2 p-3 text-sm bg-destructive/10 text-destructive rounded-md">
                <AlertCircle className="h-4 w-4" />
                <p>{micError}</p>
              </div>
            )}

            {attachments.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {attachments.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 bg-secondary rounded-full px-3 py-1"
                  >
                    <span className="text-sm">{file.name}</span>
                    <button
                      type="button"
                      onClick={() => removeAttachment(index)}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                className="flex-grow"
              />
              <input
                type="file"
                id="file-upload"
                multiple
                className="hidden"
                onChange={handleFileChange}
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => document.getElementById("file-upload")?.click()}
              >
                <Upload className="h-4 w-4" />
              </Button>
              {isRecording ? (
                <>
                  <Button type="button" variant="outline" onClick={togglePause}>
                    {isPaused ? (
                      <Play className="h-4 w-4" />
                    ) : (
                      <Pause className="h-4 w-4" />
                    )}
                  </Button>
                  <Button type="button" variant="destructive" onClick={stopRecording}>
                    <MicOff className="h-4 w-4" />
                  </Button>
                </>
              ) : (
                <Button type="button" variant="outline" onClick={startRecording}>
                  <Mic className="h-4 w-4" />
                </Button>
              )}
              <Button type="submit">
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}