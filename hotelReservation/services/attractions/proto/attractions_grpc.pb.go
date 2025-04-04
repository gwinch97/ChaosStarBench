// Code generated by protoc-gen-go-grpc. DO NOT EDIT.
// versions:
// - protoc-gen-go-grpc v1.3.0
// - protoc             v4.25.0
// source: services/attractions/proto/attractions.proto

package attractions

import (
	context "context"
	grpc "google.golang.org/grpc"
	codes "google.golang.org/grpc/codes"
	status "google.golang.org/grpc/status"
)

// This is a compile-time assertion to ensure that this generated file
// is compatible with the grpc package it is being compiled against.
// Requires gRPC-Go v1.32.0 or later.
const _ = grpc.SupportPackageIsVersion7

const (
	Attractions_NearbyRest_FullMethodName   = "/attractions.Attractions/NearbyRest"
	Attractions_NearbyMus_FullMethodName    = "/attractions.Attractions/NearbyMus"
	Attractions_NearbyCinema_FullMethodName = "/attractions.Attractions/NearbyCinema"
)

// AttractionsClient is the client API for Attractions service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://pkg.go.dev/google.golang.org/grpc/?tab=doc#ClientConn.NewStream.
type AttractionsClient interface {
	NearbyRest(ctx context.Context, in *Request, opts ...grpc.CallOption) (*Result, error)
	NearbyMus(ctx context.Context, in *Request, opts ...grpc.CallOption) (*Result, error)
	NearbyCinema(ctx context.Context, in *Request, opts ...grpc.CallOption) (*Result, error)
}

type attractionsClient struct {
	cc grpc.ClientConnInterface
}

func NewAttractionsClient(cc grpc.ClientConnInterface) AttractionsClient {
	return &attractionsClient{cc}
}

func (c *attractionsClient) NearbyRest(ctx context.Context, in *Request, opts ...grpc.CallOption) (*Result, error) {
	out := new(Result)
	err := c.cc.Invoke(ctx, Attractions_NearbyRest_FullMethodName, in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *attractionsClient) NearbyMus(ctx context.Context, in *Request, opts ...grpc.CallOption) (*Result, error) {
	out := new(Result)
	err := c.cc.Invoke(ctx, Attractions_NearbyMus_FullMethodName, in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *attractionsClient) NearbyCinema(ctx context.Context, in *Request, opts ...grpc.CallOption) (*Result, error) {
	out := new(Result)
	err := c.cc.Invoke(ctx, Attractions_NearbyCinema_FullMethodName, in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// AttractionsServer is the server API for Attractions service.
// All implementations must embed UnimplementedAttractionsServer
// for forward compatibility
type AttractionsServer interface {
	NearbyRest(context.Context, *Request) (*Result, error)
	NearbyMus(context.Context, *Request) (*Result, error)
	NearbyCinema(context.Context, *Request) (*Result, error)
	mustEmbedUnimplementedAttractionsServer()
}

// UnimplementedAttractionsServer must be embedded to have forward compatible implementations.
type UnimplementedAttractionsServer struct {
}

func (UnimplementedAttractionsServer) NearbyRest(context.Context, *Request) (*Result, error) {
	return nil, status.Errorf(codes.Unimplemented, "method NearbyRest not implemented")
}
func (UnimplementedAttractionsServer) NearbyMus(context.Context, *Request) (*Result, error) {
	return nil, status.Errorf(codes.Unimplemented, "method NearbyMus not implemented")
}
func (UnimplementedAttractionsServer) NearbyCinema(context.Context, *Request) (*Result, error) {
	return nil, status.Errorf(codes.Unimplemented, "method NearbyCinema not implemented")
}
func (UnimplementedAttractionsServer) mustEmbedUnimplementedAttractionsServer() {}

// UnsafeAttractionsServer may be embedded to opt out of forward compatibility for this service.
// Use of this interface is not recommended, as added methods to AttractionsServer will
// result in compilation errors.
type UnsafeAttractionsServer interface {
	mustEmbedUnimplementedAttractionsServer()
}

func RegisterAttractionsServer(s grpc.ServiceRegistrar, srv AttractionsServer) {
	s.RegisterService(&Attractions_ServiceDesc, srv)
}

func _Attractions_NearbyRest_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(Request)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(AttractionsServer).NearbyRest(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: Attractions_NearbyRest_FullMethodName,
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(AttractionsServer).NearbyRest(ctx, req.(*Request))
	}
	return interceptor(ctx, in, info, handler)
}

func _Attractions_NearbyMus_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(Request)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(AttractionsServer).NearbyMus(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: Attractions_NearbyMus_FullMethodName,
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(AttractionsServer).NearbyMus(ctx, req.(*Request))
	}
	return interceptor(ctx, in, info, handler)
}

func _Attractions_NearbyCinema_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(Request)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(AttractionsServer).NearbyCinema(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: Attractions_NearbyCinema_FullMethodName,
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(AttractionsServer).NearbyCinema(ctx, req.(*Request))
	}
	return interceptor(ctx, in, info, handler)
}

// Attractions_ServiceDesc is the grpc.ServiceDesc for Attractions service.
// It's only intended for direct use with grpc.RegisterService,
// and not to be introspected or modified (even as a copy)
var Attractions_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "attractions.Attractions",
	HandlerType: (*AttractionsServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "NearbyRest",
			Handler:    _Attractions_NearbyRest_Handler,
		},
		{
			MethodName: "NearbyMus",
			Handler:    _Attractions_NearbyMus_Handler,
		},
		{
			MethodName: "NearbyCinema",
			Handler:    _Attractions_NearbyCinema_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "services/attractions/proto/attractions.proto",
}
