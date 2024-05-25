# Hamster Tapper

Bot that allows you to automate the process of playing the hamster in the telegram bot "Hamster Kombat".

### Features

Taps
Upgrading

### Running

- Copy `sessings-example.yaml` to `sessings.yaml` and fill basic parameters
- Install the requirements
- Run `python create_session.py`
- Run `python -m bot`

### Parameters

| Name                 | type | description                                                                                    | default |
|----------------------|------|------------------------------------------------------------------------------------------------|---------|
| api_id               | int  | Your api_id crendetial                                                                         | -       |
| api_hash             | str  | Your api_hash crendetial                                                                       | -       |
| auto_upgrade         | bool | Enable auto upgrade                                                                            | True    |
| sleep_for_profitable | bool | Sleep if not enought energy for the most profitable upgrade                                    | True    |
| min_energy           | int  | Minimum energy after which the bot falls asleep for a while until the energy is fully restored | 90      |
| min_taps             | int  | Minimum number of taps                                                                         | 50      |
| max_taps             | int  | Maximum number of taps                                                                         | 200     |
| min_sleep_time       | int  | Minimum sleep time after taps                                                                  | 10      |
| max_sleep_time       | int  | Maximum sleep time after taps                                                                  | 25      |
