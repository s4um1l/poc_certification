import React from 'react';
import ReactMarkdown from 'react-markdown';

type MessageType = 'user' | 'agent';

interface ChatMessageProps {
  type: MessageType;
  content: string;
}

export default function ChatMessage({ type, content }: ChatMessageProps) {
  return (
    <div className={`p-4 rounded-lg max-w-3xl ${
      type === 'user' 
        ? 'bg-blue-50 ml-auto' 
        : 'bg-gray-50'
    }`}>
      <div className="flex items-start">
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          type === 'user' 
            ? 'bg-blue-500 text-white' 
            : 'bg-green-500 text-white'
        }`}>
          {type === 'user' ? 'U' : 'A'}
        </div>
        <div className="ml-3 text-sm">
          <div className="font-medium">
            {type === 'user' ? 'You' : 'AI Assistant'}
          </div>
          <div className="mt-1 prose">
            <ReactMarkdown>
              {content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
} 