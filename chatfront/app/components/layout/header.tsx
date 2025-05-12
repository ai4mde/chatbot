import * as React from 'react';
import { Link, useNavigate } from '@remix-run/react';
import { Button } from '../ui/button';
import { ThemeToggle } from './theme-toggle';
import type { CustomUser } from '../../types/auth.types';
import { Form } from '@remix-run/react';
import { UserMenu } from './user-menu';
import {
  MessageSquare,
  BookOpen,
  FileText,
  LogIn,
  Laptop,
  ChevronDown,
  Box,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { cn } from '../../lib/utils';

interface HeaderProps {
  user: CustomUser | null;
}

export const Header = React.memo(function Header({ user }: HeaderProps): JSX.Element {
  const navigate = useNavigate();

  return (
    <header className='sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60'>
      <div className='container flex h-14 items-center'>
        <div className='mr-4 flex'>
          <Link to='/' className='mr-6 flex items-center space-x-2' prefetch='intent'>
            <img 
              src='/images/logos/logo.svg' 
              alt='AI4MDE Logo' 
              className='h-6 w-6'
            />
            <span className='font-bold'>AI4MDE</span>
          </Link>
        </div>
        <div className='flex flex-1 items-center justify-between space-x-2 md:justify-end'>
          <nav className='flex items-center space-x-2'>
            
            {user && (
              <Link 
                to='/chat'
                prefetch='intent'
                className='flex items-center gap-2 px-4 py-2 rounded-md hover:bg-accent'
              >
                <Box className='h-4 w-4' />
                Chat
              </Link>
            )}

            {/* TODO: Fix and add diagrams back in */}
            {user && (
              <Button asChild variant='ghost' className='gap-2'>
                <Link to='/diagrams'>
                  <Box className='h-4 w-4' />
                  Diagrams
                </Link>
              </Button>
            )}
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant='ghost' className='gap-2'>
                  <FileText className='h-4 w-4' />
                  Docs
                  <ChevronDown className='h-4 w-4' />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align='start'>
                <DropdownMenuItem asChild>
                  <Link to='/guide' className='flex items-center gap-2'>
                    <BookOpen className='h-4 w-4' />
                    Guide
                  </Link>
                </DropdownMenuItem>
                {user && (
                  <>
                    <DropdownMenuItem asChild>
                      <Link to='/srsdocs' className='flex items-center gap-2'>
                        <FileText className='h-4 w-4' />
                        SRS Docs
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link to='/interviews' className='flex items-center gap-2'>
                        <MessageSquare className='h-4 w-4' />
                        Interviews
                      </Link>
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>

            {user && (
              <Button asChild variant='ghost' className='gap-2'>
                <a 
                  href={`https://${user.group_name}-studio.ai4mde.org`}
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  <Laptop className='h-4 w-4' />
                  Studio
                </a>
              </Button>
            )}
            <ThemeToggle />
            {user ? (
              <UserMenu user={user} />
            ) : (
              <Button asChild variant='ghost' className='gap-2'>
                <Link to='/login'>
                  <LogIn className='h-4 w-4' />
                  Login
                </Link>
              </Button>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
}); 