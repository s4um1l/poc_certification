"use client";

import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import DebugView from './DebugView';
import { FaCode, FaCommentAlt } from 'react-icons/fa';

interface Message {
  id: string;
  type: 'user' | 'agent';
  content: string;
}

interface ToolUsage {
  step: number;
  tool: string;
  input: any;
  output: any;
}

interface DebugInfo {
  tool_usage: ToolUsage[];
  message_count: number;
  message_data?: any[];
  trace_data?: any;
}

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  showDebug: boolean;
  currentDebugInfo: DebugInfo | null;
}

export default function ChatWindow() {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    showDebug: false,
    currentDebugInfo: null,
  });
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // API URL from environment variable or fallback to localhost
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    // Add welcome message
    setState(prev => ({
      ...prev,
      messages: [
        {
          id: 'welcome',
          type: 'agent',
          content: 'Hello! I can answer questions about your Shopify store sales and inventory. Try asking me something like "What were the total sales for any product in the last 30 days?" or "List products with low inventory".',
        },
      ]
    }));
  }, []);

  useEffect(() => {
    // Scroll to bottom whenever messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages]);

  const toggleDebugView = () => {
    setState(prev => ({
      ...prev,
      showDebug: !prev.showDebug
    }));
  };

  const handleSendMessage = async (message: string) => {
    if (state.isLoading) return;
    
    // Add user message to chat
    const userMessageId = Date.now().toString();
    const userMessage: Message = {
      id: userMessageId,
      type: 'user',
      content: message,
    };
    
    setState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true
    }));
    
    try {
      // Send request to backend for normal response
      const response = await axios.post(`${API_URL}/api/chat`, {
        query: message,
      });
      
      // Also fetch detailed debug info if available
      let debugInfo = response.data.debug || null;
      
      try {
        const debugResponse = await axios.post(`${API_URL}/api/debug`, {
          query: message,
        });
        
        // Merge the debug data
        debugInfo = {
          ...debugInfo,
          message_data: debugResponse.data.message_data,
          trace_data: debugResponse.data.trace_data
        };
      } catch (debugError) {
        console.warn('Could not fetch detailed debug info:', debugError);
      }
      
      // Add agent response to chat
      const agentMessage: Message = {
        id: `response-${userMessageId}`,
        type: 'agent',
        content: response.data.response,
      };
      
      // Update state with response and debug info
      setState(prev => ({
        ...prev,
        messages: [...prev.messages, agentMessage],
        isLoading: false,
        currentDebugInfo: debugInfo
      }));
    } catch (error) {
      console.error('Error fetching agent response:', error);
      
      // Add error message
      const errorMessage: Message = {
        id: `error-${userMessageId}`,
        type: 'agent',
        content: 'Sorry, I encountered an error. Please try again later.',
      };
      
      setState(prev => ({
        ...prev,
        messages: [...prev.messages, errorMessage],
        isLoading: false
      }));
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b bg-gray-50">
        <h2 className="text-lg font-semibold text-gray-800">AI Shopping Operations Assistant</h2>
        <button 
          onClick={toggleDebugView}
          className={`px-3 py-1 rounded-md flex items-center text-sm ${state.showDebug ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
        >
          {state.showDebug ? (
            <>
              <FaCommentAlt className="mr-1" /> Chat View
            </>
          ) : (
            <>
              <FaCode className="mr-1" /> Debug View
            </>
          )}
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {state.showDebug ? (
          <div className="p-4">
            <DebugView debugInfo={state.currentDebugInfo} />
          </div>
        ) : (
          <div className="p-4 space-y-4">
            {state.messages.map((message) => (
              <ChatMessage
                key={message.id}
                type={message.type}
                content={message.content}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
      
      <div className="border-t p-4">
        <ChatInput onSendMessage={handleSendMessage} disabled={state.isLoading} />
      </div>
    </div>
  );
} 