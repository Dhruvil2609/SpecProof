# Station Contracts

`proto/v1/capture_station.proto` is the authoritative process-boundary contract between the
.NET station host and the native Python capture service.

Breaking changes require a new versioned protobuf package. Generated Python and C# types must
not be edited by hand.
