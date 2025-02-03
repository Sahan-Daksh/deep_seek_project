"use client";

import React, { useEffect, useRef } from "react";

export default function WebSocketClient() {
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Replace 'localhost' & '8000' with your server address if different
    socketRef.current = new WebSocket("ws://localhost:8000/ws");

    socketRef.current.onopen = () => {
      console.log("WebSocket connected");
      socketRef.current?.send("Hello from client!");
    };

    socketRef.current.onmessage = (event) => {
      console.log("Message from server:", event.data);
    };

    socketRef.current.onclose = () => {
      console.log("WebSocket closed");
    };

    return () => {
      socketRef.current?.close();
    };
  }, []);

  return <div>WebSocket Demo</div>;
}