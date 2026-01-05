import { cn } from '@/lib/utils'

interface StatusIndicatorProps {
  status: 'online' | 'offline' | 'warning' | 'loading'
  label?: string
  showPulse?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeClasses = {
  sm: 'h-2 w-2',
  md: 'h-3 w-3',
  lg: 'h-4 w-4',
}

const pulseClasses = {
  sm: 'h-2 w-2',
  md: 'h-3 w-3',
  lg: 'h-4 w-4',
}

const statusColors = {
  online: {
    dot: 'bg-green-500',
    pulse: 'bg-green-400',
    text: 'text-green-600 dark:text-green-400',
  },
  offline: {
    dot: 'bg-red-500',
    pulse: 'bg-red-400',
    text: 'text-red-600 dark:text-red-400',
  },
  warning: {
    dot: 'bg-yellow-500',
    pulse: 'bg-yellow-400',
    text: 'text-yellow-600 dark:text-yellow-400',
  },
  loading: {
    dot: 'bg-blue-500',
    pulse: 'bg-blue-400',
    text: 'text-blue-600 dark:text-blue-400',
  },
}

export function StatusIndicator({
  status,
  label,
  showPulse = true,
  size = 'md',
  className,
}: StatusIndicatorProps) {
  const colors = statusColors[status]

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className="relative flex">
        {/* Pulse animation */}
        {showPulse && status === 'online' && (
          <span
            className={cn(
              'absolute inline-flex animate-ping rounded-full opacity-75',
              pulseClasses[size],
              colors.pulse
            )}
          />
        )}
        {/* Solid dot */}
        <span className={cn('relative inline-flex rounded-full', sizeClasses[size], colors.dot)} />
      </span>
      {label && <span className={cn('text-sm font-medium', colors.text)}>{label}</span>}
    </div>
  )
}

interface ConnectionStatusProps {
  name: string
  connected: boolean
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function ConnectionStatus({
  name,
  connected,
  showLabel = true,
  size = 'md',
  className,
}: ConnectionStatusProps) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <StatusIndicator
        status={connected ? 'online' : 'offline'}
        showPulse={connected}
        size={size}
      />
      <div className="flex flex-col">
        <span className="font-medium">{name}</span>
        {showLabel && (
          <span
            className={cn(
              'text-xs',
              connected ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
            )}
          >
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        )}
      </div>
    </div>
  )
}
