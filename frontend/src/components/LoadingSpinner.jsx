import React from 'react';
import { Loader2 } from 'lucide-react';

function LoadingSpinner({ message = 'Loading...', size = 'md', fullPage = false }) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  const textClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  const content = (
    <div className="flex flex-col items-center justify-center gap-3">
      <Loader2 className={`${sizeClasses[size]} text-blue-500 animate-spin`} />
      {message && (
        <p className={`${textClasses[size]} text-gray-400`}>{message}</p>
      )}
    </div>
  );

  if (fullPage) {
    return (
      <div className="flex items-center justify-center h-full min-h-64 w-full">
        {content}
      </div>
    );
  }

  return content;
}

export default LoadingSpinner;
