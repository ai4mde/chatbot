import * as React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Edit2, Plus, Trash2, Check } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../ui/select';
import { useReactFlow } from 'reactflow';

interface UMLNodeData {
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
}

// Common UML types
const UML_TYPES = [
  'String',
  'Integer',
  'Boolean',
  'Float',
  'Double',
  'Long',
  'Char',
  'Byte',
  'Short',
  'Date',
  'void',
  'Object',
  'List',
  'Map',
  'Set',
  'Collection',
] as const;

interface MemberEditorProps {
  value: string;
  onChange: (value: string) => void;
  onDelete: () => void;
  isMember?: boolean;
}

function MemberEditor({ value, onChange, onDelete, isMember = false }: MemberEditorProps) {
  const [visibility, name, ...rest] = value.split(/\s+/);
  const returnType = rest.join(' ').replace(/[()]/g, '').split(':')[1]?.trim() || '';
  const isAbstract = value.includes('{abstract}');

  return (
    <div className='flex items-center gap-2 mb-2'>
      <Select
        defaultValue={visibility}
        onValueChange={(v) => {
          const newValue = isMember
            ? `${v} ${name}${returnType ? ': ' + returnType : ''}${isAbstract ? ' {abstract}' : ''}`
            : `${v} ${name}()${returnType ? ': ' + returnType : ''}${isAbstract ? ' {abstract}' : ''}`;
          onChange(newValue);
        }}
      >
        <SelectTrigger className='w-16'>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value='+'>+</SelectItem>
          <SelectItem value='-'>-</SelectItem>
          <SelectItem value='#'>#</SelectItem>
          <SelectItem value='~'>~</SelectItem>
        </SelectContent>
      </Select>
      <Input
        value={name}
        onChange={(e) => {
          const newValue = isMember
            ? `${visibility} ${e.target.value}${returnType ? ': ' + returnType : ''}${isAbstract ? ' {abstract}' : ''}`
            : `${visibility} ${e.target.value}()${returnType ? ': ' + returnType : ''}${isAbstract ? ' {abstract}' : ''}`;
          onChange(newValue);
        }}
        className='flex-1'
        placeholder={isMember ? 'attribute name' : 'method name'}
      />
      <Select
        value={returnType || 'String'}
        onValueChange={(v) => {
          if (v === 'custom') return;
          const newValue = isMember
            ? `${visibility} ${name}: ${v}${isAbstract ? ' {abstract}' : ''}`
            : `${visibility} ${name}(): ${v}${isAbstract ? ' {abstract}' : ''}`;
          onChange(newValue);
        }}
      >
        <SelectTrigger className='w-24'>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {UML_TYPES.map((type) => (
            <SelectItem key={type} value={type}>
              {type}
            </SelectItem>
          ))}
          <SelectItem value='custom'>Custom...</SelectItem>
        </SelectContent>
      </Select>
      {/* Show input field for custom type */}
      {(returnType && !UML_TYPES.includes(returnType as any)) && (
        <Input
          value={returnType}
          onChange={(e) => {
            const newValue = isMember
              ? `${visibility} ${name}: ${e.target.value}${isAbstract ? ' {abstract}' : ''}`
              : `${visibility} ${name}(): ${e.target.value}${isAbstract ? ' {abstract}' : ''}`;
            onChange(newValue);
          }}
          className='w-24'
          placeholder='custom type'
        />
      )}
      <Button
        variant='ghost'
        size='icon'
        onClick={onDelete}
        className='h-8 w-8'
      >
        <Trash2 className='h-4 w-4' />
      </Button>
    </div>
  );
}

// Add handle style constant
const handleStyle = `w-2 h-2 opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity`;

function getVisibilitySymbol(visibility: string): string {
  switch (visibility) {
    case 'public': return '+';
    case 'private': return '-';
    case 'protected': return '#';
    default: return '~';
  }
}

export function ClassNode({ data, id, selected }: NodeProps<UMLNodeData>) {
  const [isEditing, setIsEditing] = React.useState(false);
  const [editedName, setEditedName] = React.useState(data.name);
  const [editedAttributes, setEditedAttributes] = React.useState(data.attributes);
  const [editedMethods, setEditedMethods] = React.useState(data.methods);
  const { deleteElements } = useReactFlow();

  const isInterface = data.type === 'interface';
  const isEnum = data.type === 'enum';
  const isAbstract = data.isAbstract;

  const handleDelete = () => {
    deleteElements({ nodes: [{ id }] });
  };

  const handleSave = () => {
    data.name = editedName;
    data.attributes = editedAttributes;
    data.methods = editedMethods;
    setIsEditing(false);
  };

  const addAttribute = () => {
    setEditedAttributes([...editedAttributes, {
      visibility: 'public',
      name: 'newAttribute',
      type: 'String',
      isStatic: false,
      isAbstract: false
    }]);
  };

  const addMethod = () => {
    setEditedMethods([...editedMethods, {
      visibility: 'public',
      name: 'newMethod',
      parameters: [],
      returnType: 'void',
      isStatic: false,
      isAbstract: false
    }]);
  };

  const removeAttribute = (index: number) => {
    setEditedAttributes(editedAttributes.filter((_, i) => i !== index));
  };

  const removeMethod = (index: number) => {
    setEditedMethods(editedMethods.filter((_, i) => i !== index));
  };

  return (
    <div className={`bg-white border border-gray-300 rounded min-w-[300px] relative group ${isInterface ? 'border-blue-300' : isEnum ? 'border-green-300' : ''}`}>
      {/* Connection handles with unique IDs */}
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
      
      {/* Class name and stereotypes */}
      <div className='border-b border-gray-300 p-2'>
        {data.stereotypes?.map((stereotype, index) => (
          <div key={index} className='text-sm text-gray-600 text-center italic'>
            {stereotype}
          </div>
        ))}
        {isEditing ? (
          <div className='pr-16'>
            <Input
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              className='text-center font-bold'
            />
          </div>
        ) : (
          <div className={`font-bold text-center ${isAbstract ? 'italic' : ''}`}>
            {data.name}
          </div>
        )}
      </div>
      
      {/* Attributes */}
      {!isInterface && (editedAttributes.length > 0 || isEditing) && (
        <div className='border-b border-gray-300 p-2'>
          {(isEditing ? editedAttributes : data.attributes).map((attr, index) => (
            isEditing ? (
              <MemberEditor
                key={index}
                value={`${attr.visibility} ${attr.name}${attr.type ? ': ' + attr.type : ''}`}
                onChange={(newValue) => {
                  const [visibility, rest] = newValue.split(' ');
                  const [name, type] = rest.split(': ');
                  const newAttributes = [...editedAttributes];
                  newAttributes[index] = {
                    ...attr,
                    visibility: visibility as 'public' | 'private' | 'protected' | 'package',
                    name,
                    type
                  };
                  setEditedAttributes(newAttributes);
                }}
                onDelete={() => {
                  setEditedAttributes(editedAttributes.filter((_, i) => i !== index));
                }}
                isMember={true}
              />
            ) : (
              <div key={index} className='text-sm font-mono mb-1'>
                {getVisibilitySymbol(attr.visibility)}{' '}
                <span className={attr.isStatic ? 'underline' : ''}>
                  {attr.name}
                </span>
                {attr.type && `: ${attr.type}`}
              </div>
            )
          ))}
          {isEditing && (
            <Button
              variant='ghost'
              size='sm'
              onClick={addAttribute}
              className='w-full mt-2'
            >
              <Plus className='h-4 w-4 mr-2' />
              Add Attribute
            </Button>
          )}
        </div>
      )}
      
      {/* Methods */}
      {data.methods.length > 0 && (
        <div className='p-2'>
          {data.methods.map((method, index) => (
            <div key={index} className={`text-sm font-mono mb-1 ${method.isAbstract ? 'italic' : ''}`}>
              {getVisibilitySymbol(method.visibility)}
              {' '}
              <span className={method.isStatic ? 'underline' : ''}>
                {method.name}
              </span>
              (
              {method.parameters.map((param, pIndex) => (
                <span key={pIndex}>
                  {pIndex > 0 && ', '}
                  {param.name}
                  {param.type && `: ${param.type}`}
                </span>
              ))}
              )
              {method.returnType && `: ${method.returnType}`}
            </div>
          ))}
        </div>
      )}
    </div>
  );
} 