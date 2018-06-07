import React from 'react';

import InputField from 'app/views/settings/components/forms/inputField';

export default class DateTimeField extends React.Component {
  render() {
    return <InputField {...this.props} type="datetime-local" />;
  }
}
