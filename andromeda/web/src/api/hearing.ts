import { useCallback, useEffect, useRef, useState } from 'react'
import { Player, Recorder } from '@/audio/audio'
import { getIdToken } from '@/firebase'

/** Protocol: sombrero/src/kavach/routers/hearing.py (module docstring). */

export interface Coaching {
  question: string
  answer: string
  score: number
  feedback: string
  better_answer: string
}

export interface Debrief {
  summary: string
  top_tips: string[]
  average_score: number | null
}

export type Entry =
  | { id: number; kind: 'ai'; text: string }
  | { id: number; kind: 'you'; text: string; coach?: Coaching }

export type HearingState = 'idle' | 'connecting' | 'live' | 'ending' | 'done' | 'error'

const WS_URL = (import.meta.env.VITE_API_URL ?? '').replace(/^http/, 'ws')
const SESSION_CAP_MS = 15 * 60 * 1000

function norm(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
}

export function useHearing(caseId: string | undefined) {
  const [state, setState] = useState<HearingState>('idle')
  const [entries, setEntries] = useState<Entry[]>([])
  const [yourTurn, setYourTurn] = useState(false)
  const [micOn, setMicOn] = useState(false)
  const [debrief, setDebrief] = useState<Debrief | null>(null)
  const [error, setError] = useState<string | null>(null)

  const ws = useRef<WebSocket | null>(null)
  const player = useRef<Player | null>(null)
  const recorder = useRef<Recorder | null>(null)
  const nextId = useRef(0)
  const cap = useRef<number | undefined>(undefined)

  const add = useCallback((kind: 'ai' | 'you', text: string) => {
    setEntries((list) => {
      const last = list[list.length - 1]
      // Transcripts arrive in small chunks: keep extending the current speaker's turn.
      if (last && last.kind === kind) {
        return [...list.slice(0, -1), { ...last, text: last.text + text }]
      }
      nextId.current += 1
      return [...list, { id: nextId.current, kind, text: text.trimStart() } as Entry]
    })
  }, [])

  const attachCoach = useCallback((c: Coaching) => {
    setEntries((list) => {
      const target = norm(c.answer).slice(0, 40)
      let idx = -1
      for (let i = list.length - 1; i >= 0; i--) {
        const e = list[i]
        if (e.kind === 'you' && !e.coach && (idx === -1 || norm(e.text).includes(target))) {
          idx = i
          if (norm(e.text).includes(target)) break
        }
      }
      if (idx === -1) return list
      const copy = [...list]
      copy[idx] = { ...(copy[idx] as Extract<Entry, { kind: 'you' }>), coach: c }
      return copy
    })
  }, [])

  const stopMic = useCallback(() => {
    recorder.current?.stop()
    recorder.current = null
    setMicOn(false)
  }, [])

  const cleanup = useCallback(() => {
    window.clearTimeout(cap.current)
    stopMic()
    player.current?.close()
    player.current = null
    ws.current?.close()
    ws.current = null
  }, [stopMic])

  useEffect(() => cleanup, [cleanup])

  const send = (msg: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(msg))
  }

  const start = useCallback(async () => {
    if (!caseId) return
    setEntries([])
    setDebrief(null)
    setError(null)
    setState('connecting')
    player.current = new Player()
    await player.current.resume()
    const token = await getIdToken()
    const socket = new WebSocket(`${WS_URL}/cases/${caseId}/hearing`)
    ws.current = socket
    socket.onopen = () => {
      socket.send(JSON.stringify({ token }))
      setState('live')
      cap.current = window.setTimeout(() => send({ end: true }), SESSION_CAP_MS)
    }
    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data as string)
      if (msg.audio) player.current?.play(msg.audio)
      else if (msg.transcript) {
        if (msg.transcript.who === 'you') {
          player.current?.interrupt()
          setYourTurn(false)
        }
        add(msg.transcript.who, msg.transcript.text)
      } else if (msg.turn_complete) setYourTurn(true)
      else if (msg.coach) attachCoach(msg.coach)
      else if (msg.done) {
        setDebrief(msg.done)
        setState('done')
        stopMic()
      } else if (msg.error) {
        setError(msg.error)
        setState('error')
      }
    }
    socket.onerror = () => {
      setError('The connection to the rehearsal dropped. Please try again.')
      setState('error')
    }
    socket.onclose = () => {
      stopMic()
      setState((s) => (s === 'live' || s === 'connecting' ? 'error' : s))
    }
  }, [caseId, add, attachCoach, stopMic])

  const toggleMic = useCallback(async () => {
    if (recorder.current) return stopMic()
    try {
      const r = new Recorder()
      await r.start((audio) => send({ audio }))
      recorder.current = r
      setMicOn(true)
    } catch {
      setError('Microphone not available. You can type your answers instead.')
    }
  }, [stopMic])

  const sendText = useCallback(
    (text: string) => {
      const clean = text.trim()
      if (!clean) return
      player.current?.interrupt()
      add('you', clean)
      setYourTurn(false)
      send({ text: clean })
    },
    [add],
  )

  const end = useCallback(() => {
    setState('ending')
    stopMic()
    send({ end: true })
  }, [stopMic])

  return { state, entries, yourTurn, micOn, debrief, error, start, toggleMic, sendText, end, cleanup }
}
