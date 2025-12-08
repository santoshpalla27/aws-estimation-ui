import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

export default memo(({ data, selected }) => {
    return (
        <div className={`shadow-lg rounded-lg bg-white dark:bg-gray-800 border-2 w-64 ${selected ? 'border-blue-500' : 'border-gray-200 dark:border-gray-700'}`}>
            <div className="flex items-center p-2 border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-900 rounded-t-lg">
                <div className="text-2xl mr-3">{data.icon || '📦'}</div>
                <div>
                    <div className="font-bold text-sm text-gray-800 dark:text-gray-200">{data.label}</div>
                    <div className="text-xs text-gray-500 max-w-[150px] truncate">{data.details || 'Not Configured'}</div>
                </div>
            </div>

            <div className="p-2 text-right">
                <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                    ${(data.cost || 0).toFixed(2)} <span className="text-xs text-gray-500 font-normal">/mo</span>
                </div>
            </div>

            {/* Input Handles */}
            <Handle
                type="target"
                position={Position.Left}
                className="w-3 h-3 bg-blue-500"
            />
            {/* Output Handles */}
            <Handle
                type="source"
                position={Position.Right}
                className="w-3 h-3 bg-blue-500"
            />
        </div>
    );
});
