'use client'

import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import { useEffect, useRef, useState } from 'react'
import {
  Bold, Italic, Underline as UnderlineIcon, Link as LinkIcon,
  List, ListOrdered, Heading2, Heading3, Braces,
} from 'lucide-react'

const VARIABLES = ['name', 'email', 'company', 'title']

interface Props {
  value: string
  onChange: (html: string) => void
  placeholder?: string
}

function ToolbarBtn({
  active, disabled, title, onClick, children,
}: {
  active?: boolean
  disabled?: boolean
  title: string
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`p-1 rounded transition-colors ${
        active
          ? 'bg-blue-100 text-blue-700'
          : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
      } disabled:opacity-30`}
    >
      {children}
    </button>
  )
}

export function TiptapEditor({ value, onChange, placeholder }: Props) {
  const [showVarMenu, setShowVarMenu] = useState(false)
  const varRef = useRef<HTMLDivElement>(null)

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      Underline,
      Link.configure({ openOnClick: false, autolink: true }),
      Placeholder.configure({ placeholder: placeholder ?? 'Write your email body…' }),
    ],
    content: value,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
    editorProps: {
      attributes: { class: 'tiptap-editor focus:outline-none min-h-[160px] px-3 py-2 text-sm text-gray-800' },
    },
  })

  // Sync external value changes (e.g. when editing an existing template)
  const lastExternal = useRef(value)
  useEffect(() => {
    if (!editor) return
    if (value !== lastExternal.current && value !== editor.getHTML()) {
      lastExternal.current = value
      editor.commands.setContent(value)
    }
  }, [value, editor])

  // Close variable menu on outside click
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (varRef.current && !varRef.current.contains(e.target as Node)) {
        setShowVarMenu(false)
      }
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [])

  function insertVariable(varName: string) {
    editor?.commands.insertContent(`{{${varName}}}`)
    setShowVarMenu(false)
    editor?.commands.focus()
  }

  function setLink() {
    const url = window.prompt('URL', editor?.getAttributes('link').href ?? '')
    if (url === null) return
    if (url === '') {
      editor?.chain().focus().extendMarkRange('link').unsetLink().run()
    } else {
      editor?.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
    }
  }

  if (!editor) return null

  return (
    <div className="border border-gray-300 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent">
      {/* Toolbar */}
      <div className="flex items-center gap-0.5 px-2 py-1 border-b border-gray-200 bg-gray-50 flex-wrap">
        <ToolbarBtn
          title="Bold" active={editor.isActive('bold')}
          onClick={() => editor.chain().focus().toggleBold().run()}
        >
          <Bold className="w-3.5 h-3.5" />
        </ToolbarBtn>
        <ToolbarBtn
          title="Italic" active={editor.isActive('italic')}
          onClick={() => editor.chain().focus().toggleItalic().run()}
        >
          <Italic className="w-3.5 h-3.5" />
        </ToolbarBtn>
        <ToolbarBtn
          title="Underline" active={editor.isActive('underline')}
          onClick={() => editor.chain().focus().toggleUnderline().run()}
        >
          <UnderlineIcon className="w-3.5 h-3.5" />
        </ToolbarBtn>

        <div className="w-px h-4 bg-gray-200 mx-1" />

        <ToolbarBtn
          title="Heading 2" active={editor.isActive('heading', { level: 2 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        >
          <Heading2 className="w-3.5 h-3.5" />
        </ToolbarBtn>
        <ToolbarBtn
          title="Heading 3" active={editor.isActive('heading', { level: 3 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        >
          <Heading3 className="w-3.5 h-3.5" />
        </ToolbarBtn>

        <div className="w-px h-4 bg-gray-200 mx-1" />

        <ToolbarBtn
          title="Bullet list" active={editor.isActive('bulletList')}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
        >
          <List className="w-3.5 h-3.5" />
        </ToolbarBtn>
        <ToolbarBtn
          title="Ordered list" active={editor.isActive('orderedList')}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
        >
          <ListOrdered className="w-3.5 h-3.5" />
        </ToolbarBtn>

        <div className="w-px h-4 bg-gray-200 mx-1" />

        <ToolbarBtn
          title="Link" active={editor.isActive('link')}
          onClick={setLink}
        >
          <LinkIcon className="w-3.5 h-3.5" />
        </ToolbarBtn>

        <div className="w-px h-4 bg-gray-200 mx-1" />

        {/* Variable insertion */}
        <div className="relative" ref={varRef}>
          <button
            type="button"
            title="Insert variable"
            onClick={() => setShowVarMenu(v => !v)}
            className="flex items-center gap-1 px-1.5 py-1 text-xs font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
          >
            <Braces className="w-3.5 h-3.5" />
            <span>Insert variable</span>
          </button>
          {showVarMenu && (
            <div className="absolute left-0 top-full mt-1 z-20 bg-white border border-gray-200 rounded-lg shadow-md py-1 min-w-[130px]">
              {VARIABLES.map(v => (
                <button
                  key={v}
                  type="button"
                  onClick={() => insertVariable(v)}
                  className="block w-full text-left px-3 py-1.5 text-xs font-mono text-gray-700 hover:bg-blue-50 hover:text-blue-700"
                >
                  {`{{${v}}}`}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Editor content */}
      <EditorContent editor={editor} />
    </div>
  )
}
