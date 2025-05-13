"use client";

import React, { useState } from 'react';
import { FaTools, FaArrowRight, FaArrowLeft, FaInfoCircle, FaFileAlt, FaCommentDots } from 'react-icons/fa';

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

interface DebugViewProps {
  debugInfo: DebugInfo | null;
}

export default function DebugView({ debugInfo }: DebugViewProps) {
  const [activeTab, setActiveTab] = useState<'tools' | 'messages' | 'trace'>('tools');
  
  if (!debugInfo) {
    return (
      <div className="bg-gray-100 p-4 rounded-md">
        <p className="text-gray-500 italic">No debug information available</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-100 p-4 rounded-md">
      {/* Tab Navigation */}
      <div className="flex border-b border-gray-300 mb-4">
        <button 
          onClick={() => setActiveTab('tools')}
          className={`px-4 py-2 flex items-center ${activeTab === 'tools' ? 'border-b-2 border-blue-500 text-blue-600 font-medium' : 'text-gray-600'}`}
        >
          <FaTools className="mr-2" /> Tool Usage
        </button>
        <button 
          onClick={() => setActiveTab('messages')}
          className={`px-4 py-2 flex items-center ${activeTab === 'messages' ? 'border-b-2 border-blue-500 text-blue-600 font-medium' : 'text-gray-600'}`}
        >
          <FaCommentDots className="mr-2" /> Messages
        </button>
        <button 
          onClick={() => setActiveTab('trace')}
          className={`px-4 py-2 flex items-center ${activeTab === 'trace' ? 'border-b-2 border-blue-500 text-blue-600 font-medium' : 'text-gray-600'}`}
        >
          <FaFileAlt className="mr-2" /> Trace
        </button>
      </div>
      
      {/* Tool Usage Tab */}
      {activeTab === 'tools' && (
        <div>
          <h3 className="font-semibold text-lg mb-2 flex items-center">
            <FaTools className="mr-2" /> Tool Usage ({debugInfo.tool_usage?.length || 0} tools)
          </h3>
          
          {(!debugInfo.tool_usage || debugInfo.tool_usage.length === 0) ? (
            <p className="text-gray-500 italic">No tool usage data available</p>
          ) : (
            <div className="space-y-4">
              {debugInfo.tool_usage.map((tool, index) => (
                <div key={index} className="border border-gray-300 rounded-md bg-white overflow-hidden">
                  <div className="bg-blue-100 p-2 font-medium flex justify-between items-center">
                    <span className="text-blue-800">
                      {index + 1}. {tool.tool}
                    </span>
                    <span className="text-xs text-gray-500">Step {tool.step}</span>
                  </div>
                  
                  <div className="p-3 grid grid-cols-1 gap-2">
                    <div>
                      <div className="flex items-center text-sm text-gray-600 mb-1">
                        <FaArrowRight className="mr-1 text-green-600" /> Input:
                      </div>
                      <pre className="bg-gray-50 p-2 rounded text-xs overflow-auto max-h-24">
                        {JSON.stringify(tool.input, null, 2)}
                      </pre>
                    </div>
                    
                    {tool.output && (
                      <div>
                        <div className="flex items-center text-sm text-gray-600 mb-1">
                          <FaArrowLeft className="mr-1 text-purple-600" /> Output:
                        </div>
                        <pre className="bg-gray-50 p-2 rounded text-xs overflow-auto max-h-32">
                          {JSON.stringify(tool.output, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* Messages Tab */}
      {activeTab === 'messages' && (
        <div>
          <h3 className="font-semibold text-lg mb-2 flex items-center">
            <FaCommentDots className="mr-2" /> Message History ({debugInfo.message_count || 0} messages)
          </h3>
          
          {(!debugInfo.message_data || debugInfo.message_data.length === 0) ? (
            <p className="text-gray-500 italic">No message data available</p>
          ) : (
            <div className="space-y-4">
              {debugInfo.message_data.map((message, index) => (
                <div key={index} className="border border-gray-300 rounded-md bg-white overflow-hidden">
                  <div className={`p-2 font-medium flex justify-between items-center ${message.type.includes('Human') ? 'bg-green-100' : 'bg-blue-100'}`}>
                    <span className={message.type.includes('Human') ? 'text-green-800' : 'text-blue-800'}>
                      {index + 1}. {message.type}
                    </span>
                    <span className="text-xs text-gray-500">#{message.index}</span>
                  </div>
                  
                  <div className="p-3 space-y-3">
                    {message.content && (
                      <div>
                        <div className="text-sm text-gray-600 mb-1 font-medium">Content:</div>
                        <div className="bg-gray-50 p-2 rounded text-sm overflow-auto max-h-32">
                          {message.content}
                        </div>
                      </div>
                    )}
                    
                    {message.tool_calls && (
                      <div>
                        <div className="text-sm text-gray-600 mb-1 font-medium">Tool Calls:</div>
                        <div className="bg-gray-50 p-2 rounded text-xs overflow-auto max-h-48">
                          <pre>{JSON.stringify(message.tool_calls, null, 2)}</pre>
                        </div>
                      </div>
                    )}
                    
                    {message.tool_call_results && (
                      <div>
                        <div className="text-sm text-gray-600 mb-1 font-medium">Tool Results:</div>
                        <div className="bg-gray-50 p-2 rounded text-xs overflow-auto max-h-48">
                          <pre>{JSON.stringify(message.tool_call_results, null, 2)}</pre>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* Trace Tab */}
      {activeTab === 'trace' && (
        <div>
          <h3 className="font-semibold text-lg mb-2 flex items-center">
            <FaFileAlt className="mr-2" /> LangGraph Trace
          </h3>
          
          {!debugInfo.trace_data ? (
            <p className="text-gray-500 italic">No trace data available</p>
          ) : (
            <div className="border border-gray-300 rounded-md bg-white">
              <div className="p-2 bg-gray-50 text-xs text-gray-700">
                Raw trace data
              </div>
              <pre className="p-3 text-xs overflow-auto max-h-96">
                {JSON.stringify(debugInfo.trace_data, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
      
      <div className="mt-4 text-xs text-gray-500 flex items-center">
        <FaInfoCircle className="mr-1" /> Total messages: {debugInfo.message_count}
      </div>
    </div>
  );
} 