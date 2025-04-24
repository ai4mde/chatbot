import { Handle, Position, useReactFlow } from 'reactflow';
import { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuTrigger } from '../ui/context-menu';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Input } from '../ui/input';
import { useState } from 'react';
import { Pencil, Trash2 } from 'lucide-react';

interface ClassNodeProps {
  id: string;
  data: {
    name: string;
    type: 'class' | 'interface' | 'enum';
    isAbstract: boolean;
    stereotypes: string[];
    attributes: Array<{
      visibility: 'public' | 'private' | 'protected' | 'package';
      name: string;
      type?: string;
      isStatic: boolean;
      isAbstract: boolean;
    }>;
    methods: Array<{
      visibility: 'public' | 'private' | 'protected' | 'package';
      name: string;
      parameters: Array<{ name: string; type?: string }>;
      returnType?: string;
      isStatic: boolean;
      isAbstract: boolean;
    }>;
  };
  selected: boolean;
}

function getVisibilitySymbol(visibility: string): string {
  switch (visibility) {
    case 'public': return '+';
    case 'private': return '-';
    case 'protected': return '#';
    default: return '~';
  }
}

export function ClassNode({ id, data, selected }: ClassNodeProps) {
  const { setNodes, getNode } = useReactFlow();
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState(data);

  const updateNode = (newData: typeof data) => {
    setNodes(nodes => 
      nodes.map(node => 
        node.id === id ? { ...node, data: newData } : node
      )
    );
  };

  const handleNameChange = (newName: string) => {
    const newData = { ...data, name: newName };
    updateNode(newData);
  };

  const handleAttributeChange = (index: number, field: string, value: any) => {
    const newAttributes = [...data.attributes];
    newAttributes[index] = { ...newAttributes[index], [field]: value };
    updateNode({ ...data, attributes: newAttributes });
  };

  const handleMethodChange = (index: number, field: string, value: any) => {
    const newMethods = [...data.methods];
    newMethods[index] = { ...newMethods[index], [field]: value };
    updateNode({ ...data, methods: newMethods });
  };

  const handleDelete = () => {
    setNodes(nodes => nodes.filter(node => node.id !== id));
  };

  return (
    <ContextMenu>
      <ContextMenuTrigger>
        <div className={`border rounded bg-background shadow-lg ${selected ? 'ring-2 ring-primary' : ''}`}>
          <Handle type='target' position={Position.Top} />
          <div className='p-2 border-b text-center font-bold'>
            {data.stereotypes?.map((stereotype, index) => (
              <div key={index} className='text-sm text-muted-foreground'>
                &laquo;{stereotype}&raquo;
              </div>
            ))}
            <div 
              className={`${data.isAbstract ? 'italic' : ''} ${selected ? 'cursor-text' : ''}`}
              contentEditable={selected}
              onBlur={(e) => handleNameChange(e.currentTarget.textContent || '')}
              suppressContentEditableWarning
            >
              {data.name}
            </div>
          </div>
          
          <div className='border-b'>
            {data.attributes.map((attr, index) => (
              <div key={index} className='p-1 text-sm group'>
                {getVisibilitySymbol(attr.visibility)}{' '}
                <span 
                  className={`${attr.isStatic ? 'underline' : ''} ${selected ? 'cursor-text' : ''}`}
                  contentEditable={selected}
                  onBlur={(e) => handleAttributeChange(index, 'name', e.currentTarget.textContent)}
                  suppressContentEditableWarning
                >
                  {attr.name}
                </span>
                {attr.type && (
                  <span
                    className={selected ? 'cursor-text' : ''}
                    contentEditable={selected}
                    onBlur={(e) => handleAttributeChange(index, 'type', e.currentTarget.textContent)}
                    suppressContentEditableWarning
                  >
                    : {attr.type}
                  </span>
                )}
                {selected && (
                  <Button
                    variant='ghost'
                    size='icon'
                    className='h-4 w-4 opacity-0 group-hover:opacity-100 ml-1'
                    onClick={() => {
                      const newAttributes = data.attributes.filter((_, i) => i !== index);
                      updateNode({ ...data, attributes: newAttributes });
                    }}
                  >
                    <Trash2 className='h-3 w-3' />
                  </Button>
                )}
              </div>
            ))}
          </div>
          
          <div>
            {data.methods.map((method, index) => (
              <div key={index} className='p-1 text-sm group'>
                {getVisibilitySymbol(method.visibility)}{' '}
                <span className={`
                  ${method.isStatic ? 'underline' : ''}
                  ${method.isAbstract ? 'italic' : ''}
                  ${selected ? 'cursor-text' : ''}
                `}>
                  <span
                    contentEditable={selected}
                    onBlur={(e) => handleMethodChange(index, 'name', e.currentTarget.textContent)}
                    suppressContentEditableWarning
                  >
                    {method.name}
                  </span>
                  (
                  {method.parameters.map((param, pIndex) => (
                    <span key={pIndex}>
                      {pIndex > 0 && ', '}
                      <span
                        contentEditable={selected}
                        onBlur={(e) => {
                          const newParams = [...method.parameters];
                          newParams[pIndex] = { ...newParams[pIndex], name: e.currentTarget.textContent || '' };
                          const newMethods = [...data.methods];
                          newMethods[index] = { ...newMethods[index], parameters: newParams };
                          updateNode({ ...data, methods: newMethods });
                        }}
                        suppressContentEditableWarning
                      >
                        {param.name}
                      </span>
                      {param.type && (
                        <span
                          contentEditable={selected}
                          onBlur={(e) => {
                            const newParams = [...method.parameters];
                            newParams[pIndex] = { ...newParams[pIndex], type: e.currentTarget.textContent || '' };
                            const newMethods = [...data.methods];
                            newMethods[index] = { ...newMethods[index], parameters: newParams };
                            updateNode({ ...data, methods: newMethods });
                          }}
                          suppressContentEditableWarning
                        >
                          : {param.type}
                        </span>
                      )}
                    </span>
                  ))}
                  )
                  {method.returnType && (
                    <span
                      contentEditable={selected}
                      onBlur={(e) => handleMethodChange(index, 'returnType', e.currentTarget.textContent)}
                      suppressContentEditableWarning
                    >
                      : {method.returnType}
                    </span>
                  )}
                </span>
                {selected && (
                  <Button
                    variant='ghost'
                    size='icon'
                    className='h-4 w-4 opacity-0 group-hover:opacity-100 ml-1'
                    onClick={() => {
                      const newMethods = data.methods.filter((_, i) => i !== index);
                      updateNode({ ...data, methods: newMethods });
                    }}
                  >
                    <Trash2 className='h-3 w-3' />
                  </Button>
                )}
              </div>
            ))}
          </div>
          <Handle type='source' position={Position.Bottom} />
        </div>
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem onSelect={() => setIsEditing(true)}>
          <Pencil className='h-4 w-4 mr-2' />
          Edit
        </ContextMenuItem>
        <ContextMenuItem onSelect={handleDelete} className='text-red-600'>
          <Trash2 className='h-4 w-4 mr-2' />
          Delete
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
} 