import * as React from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Edit2, Check, Trash2 } from 'lucide-react';

interface ActivityNodeData {
  name?: string;
  type: 'action' | 'decision' | 'start' | 'end';
}

// Add a new CSS class for handle styling
const handleStyle = `w-2 h-2 opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity`;

export function ActivityActionNode({ data, id, selected }: NodeProps<ActivityNodeData>) {
  const [isEditing, setIsEditing] = React.useState(false);
  const [editedName, setEditedName] = React.useState(data.name || '');
  const { deleteElements } = useReactFlow();

  const handleDelete = () => {
    deleteElements({ nodes: [{ id }] });
  };

  const handleSave = () => {
    data.name = editedName;
    setIsEditing(false);
  };

  return (
    <div className='bg-white border-2 border-gray-300 rounded shadow-md min-w-[200px] group'>
      {/* Connection handles */}
      <div className='top-handle-group absolute left-0 right-0 top-0 h-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-top-target`}
          type='target' 
          position={Position.Top} 
          className={handleStyle}
        />
        <Handle 
          id={`${id}-top-source`}
          type='source' 
          position={Position.Top} 
          className={handleStyle}
        />
      </div>
      
      <div className='bottom-handle-group absolute left-0 right-0 bottom-0 h-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-bottom-target`}
          type='target' 
          position={Position.Bottom} 
          className={handleStyle}
        />
        <Handle 
          id={`${id}-bottom-source`}
          type='source' 
          position={Position.Bottom} 
          className={handleStyle}
        />
      </div>
      
      <div className='left-handle-group absolute top-0 bottom-0 left-0 w-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-left-target`}
          type='target' 
          position={Position.Left} 
          className={handleStyle}
        />
        <Handle 
          id={`${id}-left-source`}
          type='source' 
          position={Position.Left} 
          className={handleStyle}
        />
      </div>
      
      <div className='right-handle-group absolute top-0 bottom-0 right-0 w-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-right-target`}
          type='target' 
          position={Position.Right} 
          className={handleStyle}
        />
        <Handle 
          id={`${id}-right-source`}
          type='source' 
          position={Position.Right} 
          className={handleStyle}
        />
      </div>

      <div className='p-2'>
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

      {/* Control buttons in top-right corner */}
      <div className='absolute top-1 right-1 flex gap-1'>
        {selected && (
          <Button
            variant='ghost'
            size='icon'
            onClick={handleDelete}
            className='h-6 w-6 hover:bg-red-100 text-red-500'
          >
            <Trash2 className='h-3 w-3' />
          </Button>
        )}
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
          className='h-6 w-6 hover:bg-accent/50'
        >
          {isEditing ? (
            <Check className='h-3 w-3' />
          ) : (
            <Edit2 className='h-3 w-3' />
          )}
        </Button>
      </div>
    </div>
  );
}

export function ActivityDecisionNode({ data, id, selected }: NodeProps<ActivityNodeData>) {
  const [isEditing, setIsEditing] = React.useState(false);
  const [editedName, setEditedName] = React.useState(data.name || '');
  const { deleteElements } = useReactFlow();

  const handleDelete = () => {
    deleteElements({ nodes: [{ id }] });
  };

  const handleSave = () => {
    data.name = editedName;
    setIsEditing(false);
  };

  return (
    <div className='relative group'>
      {/* Connection handles */}
      <div className='top-handle-group absolute left-0 right-0 top-0 h-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-top-target`}
          type='target' 
          position={Position.Top} 
          className={handleStyle}
        />
        <Handle 
          id={`${id}-top-source`}
          type='source' 
          position={Position.Top} 
          className={handleStyle}
        />
      </div>
      
      <div className='bottom-handle-group absolute left-0 right-0 bottom-0 h-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-bottom-target`}
          type='target' 
          position={Position.Bottom} 
          className={handleStyle}
        />
        <Handle 
          id={`${id}-bottom-source`}
          type='source' 
          position={Position.Bottom} 
          className={handleStyle}
        />
      </div>
      
      <div className='left-handle-group absolute top-0 bottom-0 left-0 w-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-left-target`}
          type='target' 
          position={Position.Left} 
          className={handleStyle}
        />
        <Handle 
          id={`${id}-left-source`}
          type='source' 
          position={Position.Left} 
          className={handleStyle}
        />
      </div>
      
      <div className='right-handle-group absolute top-0 bottom-0 right-0 w-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-right-target`}
          type='target' 
          position={Position.Right} 
          className={handleStyle}
        />
        <Handle 
          id={`${id}-right-source`}
          type='source' 
          position={Position.Right} 
          className={handleStyle}
        />
      </div>

      <div className='rotate-45 bg-white border-2 border-gray-300 w-[100px] h-[100px] flex items-center justify-center'>
        <div className='-rotate-45'>
          {isEditing ? (
            <Input
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              className='text-center w-24'
            />
          ) : (
            <div className='text-center font-medium'>
              {data.name}
            </div>
          )}
        </div>
      </div>

      {/* Control buttons in top-right corner */}
      <div className='absolute top-1 right-1 flex gap-1'>
        {selected && (
          <Button
            variant='ghost'
            size='icon'
            onClick={handleDelete}
            className='h-6 w-6 hover:bg-red-100 text-red-500'
          >
            <Trash2 className='h-3 w-3' />
          </Button>
        )}
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
          className='h-6 w-6 hover:bg-accent/50'
        >
          {isEditing ? (
            <Check className='h-3 w-3' />
          ) : (
            <Edit2 className='h-3 w-3' />
          )}
        </Button>
      </div>
    </div>
  );
}

export function ActivityStartNode({ data, id, selected }: NodeProps<ActivityNodeData>) {
  const { deleteElements } = useReactFlow();

  const handleDelete = () => {
    deleteElements({ nodes: [{ id }] });
  };

  return (
    <div className='relative bg-black rounded-full w-12 h-12 group'>
      {/* Connection handles */}
      <div className='top-handle-group absolute left-0 right-0 top-0 h-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-top-source`}
          type='source' 
          position={Position.Top} 
          className={handleStyle}
        />
      </div>
      
      <div className='bottom-handle-group absolute left-0 right-0 bottom-0 h-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-bottom-source`}
          type='source' 
          position={Position.Bottom} 
          className={handleStyle}
        />
      </div>
      
      <div className='left-handle-group absolute top-0 bottom-0 left-0 w-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-left-source`}
          type='source' 
          position={Position.Left} 
          className={handleStyle}
        />
      </div>
      
      <div className='right-handle-group absolute top-0 bottom-0 right-0 w-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-right-source`}
          type='source' 
          position={Position.Right} 
          className={handleStyle}
        />
      </div>

      {/* Delete button */}
      {selected && (
        <div className='absolute top-1 right-1'>
          <Button
            variant='ghost'
            size='icon'
            onClick={handleDelete}
            className='h-6 w-6 hover:bg-red-100 text-red-500'
          >
            <Trash2 className='h-3 w-3' />
          </Button>
        </div>
      )}
    </div>
  );
}

export function ActivityEndNode({ data, id, selected }: NodeProps<ActivityNodeData>) {
  const { deleteElements } = useReactFlow();

  const handleDelete = () => {
    deleteElements({ nodes: [{ id }] });
  };

  return (
    <div className='relative group'>
      <div className='bg-white border-2 border-black rounded-full w-12 h-12'>
        <div className='bg-black rounded-full w-8 h-8 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2' />
      </div>
      
      {/* Connection handles */}
      <div className='top-handle-group absolute left-0 right-0 top-0 h-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-top-target`}
          type='target' 
          position={Position.Top} 
          className={handleStyle}
        />
      </div>
      
      <div className='bottom-handle-group absolute left-0 right-0 bottom-0 h-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-bottom-target`}
          type='target' 
          position={Position.Bottom} 
          className={handleStyle}
        />
      </div>
      
      <div className='left-handle-group absolute top-0 bottom-0 left-0 w-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-left-target`}
          type='target' 
          position={Position.Left} 
          className={handleStyle}
        />
      </div>
      
      <div className='right-handle-group absolute top-0 bottom-0 right-0 w-0 flex items-center justify-center'>
        <Handle 
          id={`${id}-right-target`}
          type='target' 
          position={Position.Right} 
          className={handleStyle}
        />
      </div>

      {/* Delete button */}
      {selected && (
        <div className='absolute top-1 right-1'>
          <Button
            variant='ghost'
            size='icon'
            onClick={handleDelete}
            className='h-6 w-6 hover:bg-red-100 text-red-500'
          >
            <Trash2 className='h-3 w-3' />
          </Button>
        </div>
      )}
    </div>
  );
} 