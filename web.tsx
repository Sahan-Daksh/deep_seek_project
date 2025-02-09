"use client";

import React, { useEffect, useRef, useCallback } from "react";

interface WebSocketClientProps {
  onMessage: (message: string) => void;
  onError: (error: string) => void;
  onConnect: () => void;
}

export default function WebSocketClient({ onMessage, onError, onConnect }: WebSocketClientProps) {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    try {
      socketRef.current = new WebSocket("ws://localhost:8000/ws");

      socketRef.current.onopen = () => {
        console.log("WebSocket connected");
        onConnect();
      };

      socketRef.current.onmessage = (event) => {
        console.log("Message received:", event.data);
        onMessage(event.data);
      };

      socketRef.current.onerror = (error) => {
        console.error("WebSocket error:", error);
        onError("Connection error occurred");
      };

      socketRef.current.onclose = () => {
        console.log("WebSocket closed. Attempting to reconnect...");
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };
    } catch (error) {
      console.error("WebSocket connection error:", error);
      onError("Failed to establish connection");
    }
  }, [onMessage, onError, onConnect]);

  useEffect(() => {
    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  return null;
}