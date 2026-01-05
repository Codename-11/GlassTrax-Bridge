import { describe, it, expect } from 'vitest'
import { AxiosError } from 'axios'
import {
  parseUTCDate,
  formatLocalDateTime,
  formatLocalTime,
  formatLocalDate,
  getErrorMessage,
} from '../api'

describe('parseUTCDate', () => {
  it('appends Z to timestamps without timezone', () => {
    const result = parseUTCDate('2024-01-15T10:30:00')
    expect(result.toISOString()).toBe('2024-01-15T10:30:00.000Z')
  })

  it('handles timestamps already with Z suffix', () => {
    const result = parseUTCDate('2024-01-15T10:30:00Z')
    expect(result.toISOString()).toBe('2024-01-15T10:30:00.000Z')
  })

  it('handles timestamps with timezone offset', () => {
    const result = parseUTCDate('2024-01-15T10:30:00+00:00')
    expect(result.toISOString()).toBe('2024-01-15T10:30:00.000Z')
  })

  it('handles milliseconds', () => {
    const result = parseUTCDate('2024-01-15T10:30:00.123')
    expect(result.toISOString()).toBe('2024-01-15T10:30:00.123Z')
  })
})

describe('formatLocalDateTime', () => {
  it('returns a formatted date and time string', () => {
    const result = formatLocalDateTime('2024-01-15T10:30:00')
    // Result format depends on locale, just check it's a non-empty string
    expect(typeof result).toBe('string')
    expect(result.length).toBeGreaterThan(0)
  })
})

describe('formatLocalTime', () => {
  it('returns a formatted time string', () => {
    const result = formatLocalTime('2024-01-15T10:30:00')
    expect(typeof result).toBe('string')
    expect(result.length).toBeGreaterThan(0)
  })
})

describe('formatLocalDate', () => {
  it('returns a formatted date string', () => {
    const result = formatLocalDate('2024-01-15T10:30:00')
    expect(typeof result).toBe('string')
    expect(result.length).toBeGreaterThan(0)
  })
})

describe('getErrorMessage', () => {
  it('extracts detail string from AxiosError', () => {
    const error = new AxiosError('Request failed')
    error.response = {
      data: { detail: 'API key expired' },
      status: 401,
      statusText: 'Unauthorized',
      headers: {},
      config: {} as never,
    }

    expect(getErrorMessage(error)).toBe('API key expired')
  })

  it('handles validation error arrays', () => {
    const error = new AxiosError('Validation failed')
    error.response = {
      data: {
        detail: [{ msg: 'Field required' }, { msg: 'Invalid format' }],
      },
      status: 422,
      statusText: 'Unprocessable Entity',
      headers: {},
      config: {} as never,
    }

    expect(getErrorMessage(error)).toBe('Field required, Invalid format')
  })

  it('falls back to status text', () => {
    const error = new AxiosError('Request failed')
    error.response = {
      data: {},
      status: 500,
      statusText: 'Internal Server Error',
      headers: {},
      config: {} as never,
    }

    expect(getErrorMessage(error)).toBe('500: Internal Server Error')
  })

  it('handles AxiosError with message only', () => {
    const error = new AxiosError('Network Error')
    expect(getErrorMessage(error)).toBe('Network Error')
  })

  it('handles regular Error objects', () => {
    const error = new Error('Something went wrong')
    expect(getErrorMessage(error)).toBe('Something went wrong')
  })

  it('handles unknown error types', () => {
    expect(getErrorMessage('string error')).toBe('An unexpected error occurred')
    expect(getErrorMessage(null)).toBe('An unexpected error occurred')
    expect(getErrorMessage(undefined)).toBe('An unexpected error occurred')
  })

  it('handles validation errors without msg field', () => {
    const error = new AxiosError('Validation failed')
    error.response = {
      data: {
        detail: [
          { loc: ['body', 'name'] }, // No msg field
        ],
      },
      status: 422,
      statusText: 'Unprocessable Entity',
      headers: {},
      config: {} as never,
    }

    expect(getErrorMessage(error)).toBe('Validation error')
  })
})
