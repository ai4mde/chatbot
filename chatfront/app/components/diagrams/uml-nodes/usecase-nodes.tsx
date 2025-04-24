import * as React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Edit2, Check } from 'lucide-react';

interface UseCaseNodeData {
  name: string;
  type: 'actor' | 'useCase' | 'system';
}

export function ActorNode({ data, id }: NodeProps<UseCaseNodeData>) {
  const [isEditing, setIsEditing] = React.useState(false);
  const [editedName, setEditedName] = React.useState(data.name);

  const handleSave = () => {
    data.name = editedName;
    setIsEditing(false);
  };

  return (
    <div className='flex flex-col items-center'>
      {/* Stick figure */}
      <div className='relative mb-2'>
        {/* Head */}
        <div className='w-6 h-6 rounded-full border-2 border-black bg-white' />
        {/* Body */}
        <div className='w-[2px] h-8 bg-black mx-auto mt-1' />
        {/* Arms */}
        <div className='w-8 h-[2px] bg-black absolute top-8 left-1/2 -translate-x-1/2' />
        {/* Legs */}
        <div className='flex justify-center mt-1'>
          <div className='w-[2px] h-6 bg-black rotate-12 origin-top' />
          <div className='w-[2px] h-6 bg-black -rotate-12 origin-top' />
        </div>
      </div>

      {/* Name */}
      <div className='mt-2'>
        {isEditing ? (
          <Input
            value={editedName}
            onChange={(e) => setEditedName(e.target.value)}
            className='text-center w-32'
          />
        ) : (
          <div className='text-center font-medium'>
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

export function UseCaseNode({ data, id }: NodeProps<UseCaseNodeData>) {
  const [isEditing, setIsEditing] = React.useState(false);
  const [editedName, setEditedName] = React.useState(data.name);

  const handleSave = () => {
    data.name = editedName;
    setIsEditing(false);
  };

  return (
    <div className='relative'>
      {/* Oval shape */}
      <div className='bg-white border-2 border-gray-300 rounded-full px-8 py-4 min-w-[200px] flex items-center justify-center'>
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
      <Handle type='target' position={Position.Top} className='w-2 h-2' />
      <Handle type='target' position={Position.Bottom} className='w-2 h-2' />
    </div>
  );
}

export function SystemBoundaryNode({ data, id }: NodeProps<UseCaseNodeData>) {
  const [isEditing, setIsEditing] = React.useState(false);
  const [editedName, setEditedName] = React.useState(data.name);

  const handleSave = () => {
    data.name = editedName;
    setIsEditing(false);
  };

  return (
    <div className='relative'>
      {/* System boundary rectangle */}
      <div className='bg-transparent border-2 border-gray-300 rounded min-w-[300px] min-h-[200px]'>
        {/* System name at top */}
        <div className='absolute -top-4 left-4 bg-background px-2'>
          {isEditing ? (
            <Input
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              className='text-center w-48'
            />
          ) : (
            <div className='text-center font-medium'>
              {data.name}
            </div>
          )}
        </div>
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
    </div>
  );
} 