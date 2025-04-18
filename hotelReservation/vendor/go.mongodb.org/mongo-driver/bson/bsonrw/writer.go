// Copyright (C) MongoDB, Inc. 2017-present.
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may
// not use this file except in compliance with the License. You may obtain
// a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

package bsonrw

import (
	"go.mongodb.org/mongo-driver/bson/bsontype"
	"go.mongodb.org/mongo-driver/bson/primitive"
)

// ArrayWriter is the interface used to create a BSON or BSON adjacent array.
// Callers must ensure they call WriteArrayEnd when they have finished creating
// the array.
type ArrayWriter interface {
	WriteArrayElement() (ValueWriter, error)
	WriteArrayEnd() error
}

// DocumentWriter is the interface used to create a BSON or BSON adjacent
// document. Callers must ensure they call WriteDocumentEnd when they have
// finished creating the document.
type DocumentWriter interface {
	WriteDocumentElement(string) (ValueWriter, error)
	WriteDocumentEnd() error
}

// ValueWriter is the interface used to write BSON values. Implementations of
// this interface handle creating BSON or BSON adjacent representations of the
// values.
type ValueWriter interface {
	WriteArray() (ArrayWriter, error)
	WriteBinary(b []byte) error
	WriteBinaryWithSubtype(b []byte, btype byte) error
	WriteBoolean(bool) error
	WriteCodeWithScope(code string) (DocumentWriter, error)
	WriteDBPointer(ns string, oid primitive.ObjectID) error
	WriteDateTime(dt int64) error
	WriteDecimal128(primitive.Decimal128) error
	WriteDouble(float64) error
	WriteInt32(int32) error
	WriteInt64(int64) error
	WriteJavascript(code string) error
	WriteMaxKey() error
	WriteMinKey() error
	WriteNull() error
	WriteObjectID(primitive.ObjectID) error
	WriteRegex(pattern, options string) error
	WriteString(string) error
	WriteDocument() (DocumentWriter, error)
	WriteSymbol(symbol string) error
	WriteTimestamp(t, i uint32) error
	WriteUndefined() error
}

// ValueWriterFlusher is a superset of ValueWriter that exposes functionality to flush to the underlying buffer.
//
// Deprecated: ValueWriterFlusher will not be supported in Go Driver 2.0.
type ValueWriterFlusher interface {
	ValueWriter
	Flush() error
}

// BytesWriter is the interface used to write BSON bytes to a ValueWriter.
// This interface is meant to be a superset of ValueWriter, so that types that
// implement ValueWriter may also implement this interface.
//
// Deprecated: BytesWriter will not be supported in Go Driver 2.0.
type BytesWriter interface {
	WriteValueBytes(t bsontype.Type, b []byte) error
}

// SliceWriter allows a pointer to a slice of bytes to be used as an io.Writer.
//
// Deprecated: SliceWriter will not be supported in Go Driver 2.0.
type SliceWriter []byte

// Write writes the bytes to the underlying slice.
//
// Deprecated: SliceWriter will not be supported in Go Driver 2.0.
func (sw *SliceWriter) Write(p []byte) (int, error) {
	written := len(p)
	*sw = append(*sw, p...)
	return written, nil
}
