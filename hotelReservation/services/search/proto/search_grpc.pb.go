// Code generated by protoc-gen-go-grpc. DO NOT EDIT.
// versions:
// - protoc-gen-go-grpc v1.3.0
// - protoc             v4.25.0
// source: services/search/proto/search.proto

package proto

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
	Search_Nearby_FullMethodName = "/search.Search/Nearby"
)

// SearchClient is the client API for Search service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://pkg.go.dev/google.golang.org/grpc/?tab=doc#ClientConn.NewStream.
type SearchClient interface {
	Nearby(ctx context.Context, in *NearbyRequest, opts ...grpc.CallOption) (*SearchResult, error)
}

type searchClient struct {
	cc grpc.ClientConnInterface
}

func NewSearchClient(cc grpc.ClientConnInterface) SearchClient {
	return &searchClient{cc}
}

func (c *searchClient) Nearby(ctx context.Context, in *NearbyRequest, opts ...grpc.CallOption) (*SearchResult, error) {
	out := new(SearchResult)
	err := c.cc.Invoke(ctx, Search_Nearby_FullMethodName, in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// SearchServer is the server API for Search service.
// All implementations must embed UnimplementedSearchServer
// for forward compatibility
type SearchServer interface {
	Nearby(context.Context, *NearbyRequest) (*SearchResult, error)
	mustEmbedUnimplementedSearchServer()
}

// UnimplementedSearchServer must be embedded to have forward compatible implementations.
type UnimplementedSearchServer struct {
}

func (UnimplementedSearchServer) Nearby(context.Context, *NearbyRequest) (*SearchResult, error) {
	return nil, status.Errorf(codes.Unimplemented, "method Nearby not implemented")
}
func (UnimplementedSearchServer) mustEmbedUnimplementedSearchServer() {}

// UnsafeSearchServer may be embedded to opt out of forward compatibility for this service.
// Use of this interface is not recommended, as added methods to SearchServer will
// result in compilation errors.
type UnsafeSearchServer interface {
	mustEmbedUnimplementedSearchServer()
}

func RegisterSearchServer(s grpc.ServiceRegistrar, srv SearchServer) {
	s.RegisterService(&Search_ServiceDesc, srv)
}

func _Search_Nearby_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(NearbyRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(SearchServer).Nearby(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: Search_Nearby_FullMethodName,
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(SearchServer).Nearby(ctx, req.(*NearbyRequest))
	}
	return interceptor(ctx, in, info, handler)
}

// Search_ServiceDesc is the grpc.ServiceDesc for Search service.
// It's only intended for direct use with grpc.RegisterService,
// and not to be introspected or modified (even as a copy)
var Search_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "search.Search",
	HandlerType: (*SearchServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "Nearby",
			Handler:    _Search_Nearby_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "services/search/proto/search.proto",
}
