default: server

evaluate:
	python2 Oracle.py

test:
	python2 test_vef_spar.py
	python2 test_oracle.py

test_fast:
	python2 test_vef_spar.py
	python2 test_oracle.py -f

database:
	python2 OracleScraper.py

server:
	python2 OracleServer.py -f

serverRF:
	python2 OracleServer.py
