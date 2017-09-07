import sys
sys.path.insert(0, "lib/ln")
from .ln import rpc_pb2
import os
from . import keystore, bitcoin, daemon, interface
import socket

import concurrent.futures as futures
import time
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
import json as jsonm
from google.protobuf import json_format
import binascii

WALLET = None
NETWORK = None

def SetHdSeed(json):
  # TODO
def ConfirmedBalance(json):
  global pubk
  print(json)
  request = rpc_pb2.ConfirmedBalanceRequest()
  json_format.Parse(json, request)
  m = rpc_pb2.ConfirmedBalanceResponse()
  confs = request.confirmations
  witness = request.witness # bool

  WALLET.synchronize()
  WALLET.wait_until_synchronized()

  m.amount = sum(WALLET.get_balance())
  msg = json_format.MessageToJson(m)
  print("repl", msg)
  return msg
def NewAddress(json):
  print(json)
  request = rpc_pb2.NewAddressRequest()
  json_format.Parse(json, request)
  m = rpc_pb2.NewAddressResponse()
  if request.type == rpc_pb2.NewAddressRequest.WITNESS_PUBKEY_HASH:
    m.address = WALLET.get_unused_address()
  elif request.type == rpc_pb2.NewAddressRequest.NESTED_PUBKEY_HASH:
    assert False
  elif request.type == rpc_pb2.NewAddressRequest.PUBKEY_HASH:
    assert False
  else:
    assert False
  msg = json_format.MessageToJson(m)
  print("repl", msg)
  return msg
def FetchRootKey(json):
  global K_compressed
  print(json)
  request = rpc_pb2.FetchRootKeyRequest()
  json_format.Parse(json, request)
  m = rpc_pb2.FetchRootKeyResponse()
  m.rootKey = K_compressed
  msg = json_format.MessageToJson(m)
  print("repl", msg)
  return msg

cl = rpc_pb2.ListUnspentWitnessRequest
def ListUnspentWitness(json):
  global pubk
  req = cl()
  json_format.Parse(json, req)
  confs = req.minConfirmations
  print("confs", confs)

  WALLET.synchronize()
  WALLET.wait_until_synchronized()

  unspent = WALLET.get_utxos()
  print("unspent", unspent)
  m = rpc_pb2.ListUnspentWitnessResponse()
  for utxo in unspent:
    print(utxo)
    towire = m.utxos.add()
    towire.value = utxo.value
    towire.outPoint = rpc_pb2.OutPoint()
    towire.outPoint.hash = utxo.hash
    towire.outPoint.index = utxo.index
  #m.utxos[0].value = 
  return json_format.MessageToJson(m)

def q(pubk, cmd='blockchain.address.get_balance'):
  #print(NETWORK.synchronous_get(('blockchain.address.get_balance', [pubk]), timeout=1))
  # create an INET, STREAMing socket
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  # now connect to the web server on port 80 - the normal http port
  s.connect(("localhost", 50001))
  i = interface.Interface("localhost:50001:garbage", s)
  i.queue_request(cmd, [pubk], 42) # 42 is id
  i.send_requests()
  time.sleep(.1)
  res = i.get_responses()
  assert len(res) == 1
  print(res[0][1])
  return res[0][1]["result"]

def serve(config):
  server = SimpleJSONRPCServer(('localhost', 8432))
  server.register_function(FetchRootKey)
  server.register_function(ConfirmedBalance)
  server.register_function(NewAddress)
  server.register_function(ListUnspentWitness)
  server.register_function(SetHdSeed)
  server.serve_forever()

def test_lightning(wallet, networ, config):
  global WALLET, NETWORK, pubk, K_compressed
  WALLET = wallet
  assert networ is None

  from . import network
  assert len(network.DEFAULT_SERVERS) == 1
  networ = network.Network(config)
  networ.start()
  wallet.start_threads(networ)
  wallet.synchronize()
  print("WAITING!!!!")
  wallet.wait_until_synchronized()
  print("done")

  NETWORK = networ
  print("utxos", WALLET.get_utxos())

  assert bitcoin.deserialize_xpub(wallet.keystore.xpub)[0] == "segwit"

  pubk = wallet.get_unused_address()
  K_compressed = bytes(bytearray.fromhex(wallet.get_public_keys(pubk)[0]))
  #adr = bitcoin.public_key_to_p2wpkh(K_compressed)

  assert len(K_compressed) == 33, len(K_compressed)

  assert wallet.pubkeys_to_address(binascii.hexlify(K_compressed).decode("utf-8")) in wallet.get_addresses()
  #print(q(pubk, 'blockchain.address.listunspent'))

  serve(config)

if __name__ == '__main__':
  serve()
