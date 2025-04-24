import * as React from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
} from '@radix-ui/react-dropdown-menu';
import { Button } from '../ui/button';
import { 
  Upload, 
  Download, 
  FileText,
  Menu,
  File,
  ChevronDown,
  Plus,
  Box,
  Layout,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface DiagramHeaderProps {
  title: string;
  onImport: () => void;
  onExport: () => void;
  onNew: () => void;
  onAddClass?: () => void;
  onAddEnum?: () => void;
  onAddAction?: () => void;
  onAddDecision?: () => void;
  onAddStart?: () => void;
  onAddEnd?: () => void;
  onAddActor?: () => void;
  onAddUseCase?: () => void;
  onAddSystem?: () => void;
  onAddLifeline?: () => void;
  onAddActivation?: () => void;
  onAddMessage?: () => void;
  onLayout?: () => void;
}

export function DiagramHeader({ 
  title, 
  onImport, 
  onExport,
  onNew,
  onAddClass,
  onAddEnum,
  onAddAction,
  onAddDecision,
  onAddStart,
  onAddEnd,
  onAddActor,
  onAddUseCase,
  onAddSystem,
  onAddLifeline,
  onAddActivation,
  onAddMessage,
  onLayout,
}: DiagramHeaderProps) {
  const menuContentClass = 'bg-background border shadow-md';
  const menuItemClass = 'hover:bg-accent hover:text-accent-foreground cursor-pointer flex items-center';

  return (
    <div className='sticky top-0 z-50 flex justify-between items-center p-4 border-b bg-background'>
      <div className='flex items-center gap-2'>
        {/* File Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant='ghost' className='gap-2'>
              <FileText className='h-4 w-4' />
              File
              <ChevronDown className='h-4 w-4' />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align='start'
            className={cn('w-48 z-50', menuContentClass)}
            sideOffset={5}
          >
            <DropdownMenuItem onClick={onNew} className={menuItemClass}>
              <File className='h-4 w-4 mr-2' />
              <span>New Diagram</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator className='bg-border' />
            <DropdownMenuSub>
              <DropdownMenuSubTrigger className={menuItemClass}>
                <Upload className='h-4 w-4 mr-2' />
                <span>Load Diagram</span>
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent className={cn('z-50', menuContentClass)}>
                <DropdownMenuItem onClick={onImport} className={menuItemClass}>
                  <FileText className='h-4 w-4 mr-2' />
                  <span>PlantUML</span>
                </DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger className={menuItemClass}>
                <Download className='h-4 w-4 mr-2' />
                <span>Save Diagram</span>
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent className={cn('z-50', menuContentClass)}>
                <DropdownMenuItem onClick={onExport} className={menuItemClass}>
                  <FileText className='h-4 w-4 mr-2' />
                  <span>PlantUML</span>
                </DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Diagram Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant='ghost' className='gap-2'>
              <Box className='h-4 w-4' />
              Diagram
              <ChevronDown className='h-4 w-4' />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align='start'
            className={cn('w-48 z-50', menuContentClass)}
            sideOffset={5}
          >
            <DropdownMenuSub>
              <DropdownMenuSubTrigger className={menuItemClass}>
                <Plus className='h-4 w-4 mr-2' />
                <span>Class</span>
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent className={cn('z-50', menuContentClass)}>
                {onAddClass && (
                  <DropdownMenuItem onClick={onAddClass} className={menuItemClass}>
                    <Box className='h-4 w-4 mr-2' />
                    <span>Add Class</span>
                  </DropdownMenuItem>
                )}
                {onAddEnum && (
                  <DropdownMenuItem onClick={onAddEnum} className={menuItemClass}>
                    <Box className='h-4 w-4 mr-2' />
                    <span>Add Enum</span>
                  </DropdownMenuItem>
                )}
              </DropdownMenuSubContent>
            </DropdownMenuSub>

            <DropdownMenuSub>
              <DropdownMenuSubTrigger className={menuItemClass}>
                <Plus className='h-4 w-4 mr-2' />
                <span>Activity</span>
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent className={cn('z-50', menuContentClass)}>
                {onAddAction && (
                  <DropdownMenuItem onClick={onAddAction} className={menuItemClass}>
                    <Box className='h-4 w-4 mr-2' />
                    <span>Add Action</span>
                  </DropdownMenuItem>
                )}
                {onAddDecision && (
                  <DropdownMenuItem onClick={onAddDecision} className={menuItemClass}>
                    <Box className='h-4 w-4 mr-2' />
                    <span>Add Decision</span>
                  </DropdownMenuItem>
                )}
                {onAddStart && (
                  <DropdownMenuItem onClick={onAddStart} className={menuItemClass}>
                    <Box className='h-4 w-4 mr-2' />
                    <span>Add Start</span>
                  </DropdownMenuItem>
                )}
                {onAddEnd && (
                  <DropdownMenuItem onClick={onAddEnd} className={menuItemClass}>
                    <Box className='h-4 w-4 mr-2' />
                    <span>Add End</span>
                  </DropdownMenuItem>
                )}
              </DropdownMenuSubContent>
            </DropdownMenuSub>

            <DropdownMenuSub>
              <DropdownMenuSubTrigger className={menuItemClass}>
                <Plus className='h-4 w-4 mr-2' />
                <span>Use Case</span>
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent className={cn('z-50', menuContentClass)}>
                {onAddActor && (
                  <DropdownMenuItem onClick={onAddActor} className={menuItemClass}>
                    <Box className='h-4 w-4 mr-2' />
                    <span>Add Actor</span>
                  </DropdownMenuItem>
                )}
                {onAddUseCase && (
                  <DropdownMenuItem onClick={onAddUseCase} className={menuItemClass}>
                    <Box className='h-4 w-4 mr-2' />
                    <span>Add Use Case</span>
                  </DropdownMenuItem>
                )}
                {onAddSystem && (
                  <DropdownMenuItem onClick={onAddSystem} className={menuItemClass}>
                    <Box className='h-4 w-4 mr-2' />
                    <span>Add System</span>
                  </DropdownMenuItem>
                )}
              </DropdownMenuSubContent>
            </DropdownMenuSub>

            <DropdownMenuSub>
              <DropdownMenuSubTrigger className={menuItemClass}>
                <Plus className='h-4 w-4 mr-2' />
                <span>Sequence</span>
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent className={cn('z-50', menuContentClass)}>
                {onAddLifeline && (
                  <DropdownMenuItem onClick={onAddLifeline} className={menuItemClass}>
                    <Box className='h-4 w-4 mr-2' />
                    <span>Add Lifeline</span>
                  </DropdownMenuItem>
                )}
                {onAddActivation && (
                  <DropdownMenuItem onClick={onAddActivation} className={menuItemClass}>
                    <Box className='h-4 w-4 mr-2' />
                    <span>Add Activation</span>
                  </DropdownMenuItem>
                )}
                {onAddMessage && (
                  <DropdownMenuItem onClick={onAddMessage} className={menuItemClass}>
                    <Box className='h-4 w-4 mr-2' />
                    <span>Add Message</span>
                  </DropdownMenuItem>
                )}
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <h1 className='text-xl font-semibold'>{title}</h1>

      {onLayout && (
        <Button
          variant='outline'
          size='sm'
          onClick={onLayout}
          className='ml-2'
        >
          <Layout className='h-4 w-4 mr-2' />
          Auto Layout
        </Button>
      )}
    </div>
  );
} 