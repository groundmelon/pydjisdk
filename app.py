from pydjisdk import SDKApplication
import yaml

if __name__ == '__main__':
    with open('config.yaml', 'r') as f:
        config = yaml.load(f.read(), Loader=yaml.Loader)

    app = SDKApplication(
        app_id=config['app_id'],
        aes256_key=config['enc_key'],
        port=config['port'],
        baudrate=config['baudrate'])

    operation_table = dict((
        (0, app.get_api_version),
        (1, app.active_api),
        (2, app.acquire_control),
        (3, app.release_control),
    ))

    prompt = '\n'.join(['--------------------',
                        ' 0: get_api_version',
                        ' 1: active api',
                        ' 2: acquire control',
                        ' 3: release control',
                        '--------------------\n'
                        ])

    app.launch()
    print(prompt)
    while True:
        try:
            buf = raw_input('Choose operation:')
            n = int(buf)
            operation_table[n]()

        except KeyboardInterrupt, e:
            app.close()
            print('App closed')
            break
        except ValueError, e:
            print('Invalid input!')
            print(prompt)
        except KeyError, e:
            print('Invalid choose!')
            print(prompt)
