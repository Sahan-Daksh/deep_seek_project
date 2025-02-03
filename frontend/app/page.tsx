"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { Mic, MicOff, Pause, Play, Send, Upload, X, AlertCircle, MessageSquare, Plus, Square } from "lucide-react";
import { formatDistance } from "date-fns";
////
//import WebSocketClient from "./app/WebSocketClient"; // <-- Import here


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
  const [transcription, setTranscription] = useState("");
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout>();
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    if (isRecording && !isPaused) {
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isRecording, isPaused]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const startSpeechRecognition = () => {
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      
      recognitionRef.current.onresult = (event) => {
        let finalTranscript = '';
        let interimTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }
        
        setTranscription(finalTranscript || interimTranscript);
        setInput(finalTranscript || interimTranscript);
      };
      
      recognitionRef.current.start();
    }
  };

  const startRecording = async () => {
    try {
      setMicError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        if (transcription) {
          addMessage(transcription);
        }
        setTranscription("");
        setRecordingTime(0);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setIsPaused(false);
      startSpeechRecognition();
    } catch (err) {
      console.error("Error accessing microphone:", err);
      let errorMessage = "Failed to access microphone";
      
      if (err instanceof Error) {
        if (err.name === "NotAllowedError") {
          errorMessage = "Microphone permission was denied. Please allow microphone access to record audio.";
        } else if (err.name === "NotFoundError") {
          errorMessage = "No microphone found. Please connect a microphone and try again.";
        } else if (err.name === "NotReadableError") {
          errorMessage = "Microphone is already in use by another application.";
        }
      }
      
      setMicError(errorMessage);
      setIsRecording(false);
      setIsPaused(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsRecording(false);
      setIsPaused(false);
    }
  };

  const togglePause = () => {
    if (mediaRecorderRef.current && isRecording) {
      if (isPaused) {
        mediaRecorderRef.current.resume();
        recognitionRef.current?.start();
      } else {
        mediaRecorderRef.current.pause();
        recognitionRef.current?.stop();
      }
      setIsPaused(!isPaused);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setAttachments(Array.from(e.target.files));
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const startNewChat = () => {
    const newChatId = Math.random().toString(36).substring(7);
    setCurrentChatId(newChatId);
    setMessages([]);
  };

  const endCurrentChat = () => {
    if (messages.length > 0) {
      const newChat: Chat = {
        id: currentChatId || Math.random().toString(36).substring(7),
        title: messages[0].content.slice(0, 30) + (messages[0].content.length > 30 ? "..." : ""),
        lastMessage: messages[messages.length - 1].content,
        timestamp: new Date(),
        messages: [...messages]
      };
      
      setRecentChats(prev => {
        const updated = [newChat, ...prev].slice(0, 10);
        return updated;
      });
    }
    
    startNewChat();
  };

  const loadChat = (chat: Chat) => {
    setCurrentChatId(chat.id);
    setMessages(chat.messages);
  };

  const addMessage = (content: string, messageAttachments?: Message["attachments"]) => {
    const newMessage: Message = {
      id: Math.random().toString(36).substring(7),
      content,
      role: "user",
      timestamp: new Date(),
      attachments: messageAttachments
    };
    setMessages(prev => [...prev, newMessage]);

    // Simulate bot response
    setTimeout(() => {
      const botMessage: Message = {
        id: Math.random().toString(36).substring(7),
        content: "This is a simulated response. Integrate your chatbot API here.",
        role: "assistant",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
    }, 1000);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() || attachments.length > 0) {
      const messageAttachments = attachments.map(file => ({
        name: file.name,
        url: URL.createObjectURL(file),
        type: file.type
      }));
      addMessage(input, messageAttachments);
      setInput("");
      setAttachments([]);
    }
  };

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <div className="w-64 bg-card border-r border-border p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Chats</h2>
          <Button
            variant="outline"
            size="sm"
            onClick={startNewChat}
            className="h-8 w-8 p-0"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <ScrollArea className="h-[calc(100vh-6rem)]">
          <div className="space-y-2">
            {recentChats.map((chat) => (
              <div
                key={chat.id}
                className={`p-3 rounded-lg hover:bg-accent cursor-pointer transition-colors ${
                  chat.id === currentChatId ? 'bg-accent' : ''
                }`}
                onClick={() => loadChat(chat)}
              >
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{chat.title}</span>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  {formatDistance(chat.timestamp, new Date(), { addSuffix: true })}
                </p>
              </div>
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
                      {message.attachments && message.attachments.length > 0 && (
                        <div className="mt-2 space-y-2">
                          {message.attachments.map((attachment, index) => (
                            <div key={index} className="flex items-center gap-2">
                              <Upload className="h-4 w-4" />
                              <a
                                href={attachment.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm underline"
                              >
                                {attachment.name}
                              </a>
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
                {transcription && (
                  <div className="flex justify-end">
                    <div className="max-w-[80%] rounded-lg p-4 bg-secondary/50 text-muted-foreground">
                      <p>{transcription}</p>
                    </div>
                  </div>
                )}
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
              <Button type="submit">
                <Send className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex items-center gap-2">
              {!isRecording ? (
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={startRecording}
                  className="relative"
                >
                  <Mic className="h-4 w-4 mr-2" />
                  Record
                </Button>
              ) : (
                <>
                  <Button type="button" variant="outline" onClick={togglePause}>
                    {isPaused ? (
                      <Play className="h-4 w-4 mr-2" />
                    ) : (
                      <Pause className="h-4 w-4 mr-2" />
                    )}
                    {isPaused ? "Resume" : "Pause"}
                  </Button>
                  <Button type="button" variant="destructive" onClick={stopRecording}>
                    <MicOff className="h-4 w-4 mr-2" />
                    Stop
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    {formatTime(recordingTime)}
                  </span>
                </>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}