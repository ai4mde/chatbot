import * as React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Edit2, Check } from 'lucide-react';

interface SequenceNodeData {
  name: string;
  type: 'lifeline' | 'activation' | 'message';
  isActive?: boolean;
}

export function LifelineNode({ data, id }: NodeProps<SequenceNodeData>) {
  const [isEditing, setIsEditing] = React.useState(false);
  const [editedName, setEditedName] = React.useState(data.name);

  const handleSave = () => {
    data.name = editedName;
    setIsEditing(false);
  };

  return (
    <div className='flex flex-col items-center'>
      {/* Object/Class Box */}
      <div className='bg-white border-2 border-gray-300 rounded px-4 py-2 min-w-[120px]'>
        {isEditing ? (
          <Input
            value={editedName}
            onChange={(e) => setEditedName(e.target.value)}
            className='text-center'
          />
        ) : (
          <div className='text-center font-medium'>
            {data.name}
          </div>
        )}
      </div>

      {/* Lifeline (dashed vertical line) */}
      <div className='w-0 h-[300px] border-l-2 border-dashed border-gray-300 mt-2' />

      {/* Edit button */}
      <div className='absolute -right-10 top-0'>
        <Button
          variant='ghost'
          size='icon'
          onClick={() => {
            if (isEditing) {
              handleSave();
            } else {
              setIsEditing(true);
            }
          }}
          className='h-8 w-8'
        >
          {isEditing ? (
            <Check className='h-4 w-4' />
          ) : (
            <Edit2 className='h-4 w-4' />
          )}
        </Button>
      </div>

      {/* Connection points */}
      <Handle type='source' position={Position.Right} className='w-2 h-2' />
      <Handle type='target' position={Position.Left} className='w-2 h-2' />
    </div>
  );
}

export function ActivationNode({ data, id }: NodeProps<SequenceNodeData>) {
  return (
    <div className='relative'>
      {/* Activation bar */}
      <div className='bg-blue-100 border-2 border-blue-300 w-4 h-[100px]' />

      {/* Connection points */}
      <Handle type='source' position={Position.Right} className='w-2 h-2' />
      <Handle type='target' position={Position.Left} className='w-2 h-2' />
      <Handle type='target' position={Position.Top} className='w-2 h-2' />
      <Handle type='source' position={Position.Bottom} className='w-2 h-2' />
    </div>
  );
}

export function MessageNode({ data, id }: NodeProps<SequenceNodeData>) {
  const [isEditing, setIsEditing] = React.useState(false);
  const [editedName, setEditedName] = React.useState(data.name);

  const handleSave = () => {
    data.name = editedName;
    setIsEditing(false);
  };

  return (
    <div className='relative'>
      {/* Message label */}
      <div className='absolute -top-6 left-1/2 -translate-x-1/2 min-w-[100px]'>
        {isEditing ? (
          <Input
            value={editedName}
            onChange={(e) => setEditedName(e.target.value)}
            className='text-center text-sm'
          />
        ) : (
          <div className='text-center text-sm'>
            {data.name}
          </div>
        )}
      </div>

      {/* Edit button */}
      <div className='absolute -right-10 top-0'>
        <Button
          variant='ghost'
          size='icon'
          onClick={() => {
            if (isEditing) {
              handleSave();
            } else {
              setIsEditing(true);
            }
          }}
          className='h-8 w-8'
        >
          {isEditing ? (
            <Check className='h-4 w-4' />
          ) : (
            <Edit2 className='h-4 w-4' />
          )}
        </Button>
      </div>

      {/* Connection points */}
      <Handle type='source' position={Position.Right} className='w-2 h-2' />
      <Handle type='target' position={Position.Left} className='w-2 h-2' />
    </div>
  );
} 